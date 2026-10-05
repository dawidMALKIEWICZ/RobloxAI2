--!strict
-- Ambient life for the map (client only, presentation only).
--
-- Animates every descendant of the map that has an "Anim" attribute. Works on a single BasePart
-- or on a Model (all its parts move rigidly with a reference part: PrimaryPart, else a child
-- named "Pivot", else the child MeshPart "Mesh", else the first BasePart found).
-- Motions are offsets from the pivot the object had when it was first seen, so the map files
-- can be read and edited as a still scene.
--
--   Anim = "Spin"  SpinAxis (Vector3, reference part's local space, default 0,1,0)
--                  SpinSpeed (rad/s, default 1)
--   Anim = "Bob"   BobHeight (studs, default 0.5), BobSpeed (rad/s, default 1.5),
--                  BobTilt (degrees of gentle rocking, default 0)
--   Anim = "Sail"  SailRadius (studs, default 20), SailSpeed (rad/s, default 0.2),
--                  SailCenter (Vector3 world, optional; default = start pivot + flat RightVector
--                  * SailRadius). The object circles the centre, moving along its LookVector
--                  at the start, and keeps facing along the circle. A small bob is added.
--   Anim = "Jump"  JumpHeight (studs, default 6), JumpPeriod (s, default 8),
--                  JumpLength (studs, default 14), JumpDuration (s, default 1.4).
--                  Leaps along the flat LookVector, arc centred on the start pivot; between
--                  jumps it waits 8 studs under the start pivot (under the sea).
--   AnimPhase (number, optional) shifts the timing; otherwise a phase is derived from position.
--
-- API:
--   local Ambient = require(ReplicatedStorage.Ambient)
--   Ambient.start(map: Instance)          -- safe to call once per map; returns nothing
--   Ambient.SetQuality(q: "High" | "Low") -- Low: only objects within 200 studs, at 20 Hz
--   Ambient.stop()
--
-- Cost: instances and base pivots are cached once; each frame only objects near the camera
-- are moved (> 450 studs skipped, far ones updated at 15 Hz) with one workspace:BulkMoveTo.
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

type Entry = {
	inst: Instance,
	kind: string,
	ref: BasePart?,
	base: CFrame,
	pos: Vector3,
	parts: { BasePart },
	offsets: { CFrame },
	phase: number,
	nextAt: number,
	-- parameters
	axis: Vector3,
	speed: number,
	height: number,
	tilt: number,
	radius: number,
	center: Vector3,
	theta0: number,
	dir: number,
	period: number,
	length: number,
	duration: number,
	relRot: CFrame,
}

local Ambient = {}

local MAX_DIST_HIGH = 450
local NEAR_DIST_HIGH = 160
local FAR_RATE_HIGH = 1 / 15
local MAX_DIST_LOW = 200
local RATE_LOW = 1 / 20
local HIDE_DEPTH = 8

local quality: string = "High"
local entries: { Entry } = {}
local byInst: { [Instance]: Entry } = {}
local byPart: { [BasePart]: Entry } = {}
local connections: { RBXScriptConnection } = {}
local startClock = os.clock()
local moveParts: { BasePart } = {}
local moveCFrames: { CFrame } = {}

local function num(inst: Instance, name: string, default: number): number
	local v = inst:GetAttribute(name)
	return if typeof(v) == "number" then v else default
end

local function vec(inst: Instance, name: string, default: Vector3?): Vector3?
	local v = inst:GetAttribute(name)
	return if typeof(v) == "Vector3" then v else default
end

local function flat(v: Vector3): Vector3
	local f = Vector3.new(v.X, 0, v.Z)
	return if f.Magnitude > 1e-4 then f.Unit else Vector3.new(0, 0, -1)
end

-- yaw-only frame looking along the flat LookVector; relRot maps it back to the real rotation
local function yawFrame(cf: CFrame): CFrame
	return CFrame.lookAt(Vector3.zero, flat(cf.LookVector))
end

local function referencePart(inst: Instance): BasePart?
	if inst:IsA("BasePart") then
		return inst
	end
	if inst:IsA("Model") and inst.PrimaryPart then
		return inst.PrimaryPart
	end
	for _, name in { "Pivot", "Mesh" } do
		local c = inst:FindFirstChild(name)
		if c and c:IsA("BasePart") then
			return c
		end
	end
	return inst:FindFirstChildWhichIsA("BasePart", true)
end

local function addPart(e: Entry, p: BasePart)
	if byPart[p] then
		return
	end
	byPart[p] = e
	table.insert(e.parts, p)
	-- streamed-in parts arrive at their original (server) CFrame, so this is always exact
	table.insert(e.offsets, e.base:ToObjectSpace(p.CFrame))
end

local function removePart(p: BasePart)
	local e = byPart[p]
	if not e then
		return
	end
	byPart[p] = nil
	local i = table.find(e.parts, p)
	if i then
		table.remove(e.parts, i)
		table.remove(e.offsets, i)
	end
end

local function register(inst: Instance)
	if byInst[inst] then
		return
	end
	local kind = inst:GetAttribute("Anim")
	if typeof(kind) ~= "string" then
		return
	end
	local ref = referencePart(inst)
	if not ref then
		return -- nothing streamed in yet; DescendantAdded will try again
	end
	local base = ref.CFrame
	local pos = base.Position
	local e: Entry = {
		inst = inst,
		kind = kind,
		ref = ref,
		base = base,
		pos = pos,
		parts = {},
		offsets = {},
		phase = num(inst, "AnimPhase", (pos.X * 0.137 + pos.Z * 0.071) % (math.pi * 2)),
		nextAt = 0,
		axis = Vector3.yAxis,
		speed = 1,
		height = 0,
		tilt = 0,
		radius = 0,
		center = pos,
		theta0 = 0,
		dir = 1,
		period = 8,
		length = 14,
		duration = 1.4,
		relRot = yawFrame(base):Inverse() * base.Rotation,
	}
	if kind == "Spin" then
		local axis = vec(inst, "SpinAxis", Vector3.yAxis) :: Vector3
		e.axis = if axis.Magnitude > 1e-4 then axis.Unit else Vector3.yAxis
		e.speed = num(inst, "SpinSpeed", 1)
	elseif kind == "Bob" then
		e.height = num(inst, "BobHeight", 0.5)
		e.speed = num(inst, "BobSpeed", 1.5)
		e.tilt = math.rad(num(inst, "BobTilt", 0))
	elseif kind == "Sail" then
		e.radius = num(inst, "SailRadius", 20)
		e.speed = math.abs(num(inst, "SailSpeed", 0.2))
		local right = flat(base.RightVector)
		local c = vec(inst, "SailCenter", nil) or (pos + right * e.radius)
		e.center = Vector3.new(c.X, pos.Y, c.Z)
		local d = pos - e.center
		e.theta0 = math.atan2(d.Z, d.X)
		-- travel direction for increasing theta; flip so the start motion follows LookVector
		local tangent = Vector3.new(-math.sin(e.theta0), 0, math.cos(e.theta0))
		e.dir = if tangent:Dot(flat(base.LookVector)) >= 0 then 1 else -1
	elseif kind == "Jump" then
		e.height = num(inst, "JumpHeight", 6)
		e.period = math.max(num(inst, "JumpPeriod", 8), 0.5)
		e.length = num(inst, "JumpLength", 14)
		e.duration = math.clamp(num(inst, "JumpDuration", 1.4), 0.2, e.period)
	else
		return
	end
	byInst[inst] = e
	table.insert(entries, e)
	if inst:IsA("BasePart") then
		addPart(e, inst)
	else
		for _, d in inst:GetDescendants() do
			if d:IsA("BasePart") then
				addPart(e, d)
			end
		end
	end
end

local function unregister(inst: Instance)
	local e = byInst[inst]
	if not e then
		return
	end
	byInst[inst] = nil
	for _, p in e.parts do
		byPart[p] = nil
	end
	local i = table.find(entries, e)
	if i then
		table.remove(entries, i)
	end
end

-- pose of the reference pivot at time t
local function pose(e: Entry, t: number): CFrame
	local kind = e.kind
	if kind == "Spin" then
		return e.base * CFrame.fromAxisAngle(e.axis, e.speed * t + e.phase)
	elseif kind == "Bob" then
		local a = e.speed * t + e.phase
		local cf = e.base + Vector3.new(0, math.sin(a) * e.height, 0)
		if e.tilt ~= 0 then
			cf *= CFrame.Angles(math.sin(a * 0.7) * e.tilt, 0, math.cos(a * 0.9) * e.tilt)
		end
		return cf
	elseif kind == "Sail" then
		local dTheta = e.dir * e.speed * t
		local c = e.center
		local cf = CFrame.new(c) * CFrame.Angles(0, -dTheta, 0) * CFrame.new(-c) * e.base
		local a = 1.3 * t + e.phase
		return cf * CFrame.Angles(math.sin(a) * 0.03, 0, math.cos(a * 0.8) * 0.04)
			+ Vector3.new(0, math.sin(a) * 0.25, 0)
	else -- Jump
		local cycle = (t + e.phase * e.period / (math.pi * 2)) % e.period
		if cycle >= e.duration then
			return e.base - Vector3.new(0, HIDE_DEPTH, 0)
		end
		local f = cycle / e.duration
		local fwd = flat(e.base.LookVector)
		local h = e.height
		local p = e.base.Position + fwd * ((f - 0.5) * e.length) + Vector3.new(0, 4 * h * f * (1 - f), 0)
		local slope = 4 * h * (1 - 2 * f) / math.max(e.length, 0.1)
		local look = (fwd + Vector3.new(0, slope, 0)).Unit
		return CFrame.lookAt(p, p + look) * e.relRot
	end
end

local function step()
	local cam = Workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local now = os.clock()
	local t = now - startClock
	local low = quality == "Low"
	local maxDist = if low then MAX_DIST_LOW else MAX_DIST_HIGH
	for _, e in entries do
		local n = #e.parts
		if n == 0 or now < e.nextAt then
			continue
		end
		local dist = (e.pos - camPos).Magnitude
		if dist > maxDist + e.radius then
			e.nextAt = now + 0.5 -- re-check distance twice a second
			continue
		end
		if low then
			e.nextAt = now + RATE_LOW
		elseif dist > NEAR_DIST_HIGH + e.radius then
			e.nextAt = now + FAR_RATE_HIGH
		else
			e.nextAt = 0
		end
		local cf = pose(e, t)
		if e.kind == "Sail" then
			e.pos = cf.Position
		end
		local parts, offsets = e.parts, e.offsets
		for i = 1, n do
			table.insert(moveParts, parts[i])
			table.insert(moveCFrames, cf * offsets[i])
		end
	end
	if #moveParts > 0 then
		Workspace:BulkMoveTo(moveParts, moveCFrames, Enum.BulkMoveMode.FireCFrameChanged)
		table.clear(moveParts)
		table.clear(moveCFrames)
	end
end

function Ambient.SetQuality(q: string)
	quality = if q == "Low" then "Low" else "High"
	for _, e in entries do
		e.nextAt = 0
	end
end

function Ambient.stop()
	for _, c in connections do
		c:Disconnect()
	end
	table.clear(connections)
	table.clear(entries)
	table.clear(byInst)
	table.clear(byPart)
end

function Ambient.start(map: Instance)
	Ambient.stop()
	startClock = os.clock()
	for _, d in map:GetDescendants() do
		if d:GetAttribute("Anim") ~= nil then
			register(d)
		end
	end
	table.insert(connections, map.DescendantAdded:Connect(function(d: Instance)
		if d:GetAttribute("Anim") ~= nil then
			register(d)
			return
		end
		if d:IsA("BasePart") then
			-- a part streamed into an animated model
			local a = d.Parent
			while a and a ~= map do
				local e = byInst[a]
				if e then
					addPart(e, d)
					return
				end
				if a:GetAttribute("Anim") ~= nil then
					register(a) -- its first part just arrived
					return
				end
				a = a.Parent
			end
		end
	end))
	table.insert(connections, map.DescendantRemoving:Connect(function(d: Instance)
		if byInst[d] then
			unregister(d)
		elseif d:IsA("BasePart") then
			removePart(d)
		end
	end))
	table.insert(connections, RunService.RenderStepped:Connect(step))
end

return Ambient

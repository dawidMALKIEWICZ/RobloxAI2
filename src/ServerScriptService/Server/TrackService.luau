-- Builds each player's track from their rolled pieces and drives their car along it.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Stats = require(ReplicatedStorage.Shared.Stats)
local PlotService = require(script.Parent.PlotService)

local Assets = ReplicatedStorage:WaitForChild("Assets")

local TrackService = {}

type Waypoint = { cf: CFrame, teleport: boolean, boost: number, pieceEnd: string? }
type State = {
	player: Player,
	plot: Model,
	pieces: { string },
	path: { Waypoint },
	lengths: { number },
	car: Model?,
	seg: number,
	dist: number,
}

local states: { [Player]: State } = {}
local onEarn: ((Player, string, Vector3) -> ())? = nil
local CAR_OFFSET = CFrame.new(0, 0.5, 0)

local function flatLook(cf: CFrame): Vector3
	local v = Vector3.new(cf.LookVector.X, 0, cf.LookVector.Z)
	return if v.Magnitude > 1e-3 then v.Unit else Vector3.new(0, 0, -1)
end

-- Turning pieces exist as _R and _L; pick the side that keeps the track heading outward.
local function chooseVariant(pieceId: string, chain: CFrame, origin: CFrame): string
	local piece = Stats.Pieces[pieceId]
	if not piece.turns then
		return pieceId
	end
	local out = flatLook(origin)
	local head = flatLook(chain)
	local crossY = out:Cross(head).Y
	if crossY < -0.1 then
		return pieceId .. "_L" -- already turned right, come back left
	elseif crossY > 0.1 then
		return pieceId .. "_R"
	end
	local lateral = (chain.Position - origin.Position):Dot(origin.RightVector)
	return pieceId .. (if lateral > 0 then "_L" else "_R")
end

local function readPath(folder: Instance, chain: CFrame, pieceId: string, path: { Waypoint })
	local wps = folder:GetChildren()
	table.sort(wps, function(a, b)
		return tonumber(a.Name) < tonumber(b.Name)
	end)
	-- waypoint 1 sits on the previous piece's exit, skip it
	for i = 2, #wps do
		local wp = wps[i] :: BasePart
		table.insert(path, {
			cf = chain * wp.CFrame,
			teleport = wp:GetAttribute("Teleport") == true,
			boost = wp:GetAttribute("Boost") or 1,
			pieceEnd = if i == #wps then pieceId else nil,
		})
	end
end

local function buildPath(state: State)
	local plot = state.plot
	local trackFolder = plot:FindFirstChild("Track") :: Folder
	trackFolder:ClearAllChildren()
	local start = plot:FindFirstChild("TrackStart") :: Model
	local origin = (start:FindFirstChild("TrackOrigin") :: BasePart).CFrame
	local carStart = (start:FindFirstChild("CarStart") :: BasePart).CFrame
	local path: { Waypoint } = {}
	-- start straight on the island
	local n = 8
	for i = 0, n do
		table.insert(path, {
			cf = carStart:Lerp(origin, i / n),
			teleport = false,
			boost = 1,
			pieceEnd = nil,
		})
	end
	local chain = origin
	local templates = Assets:WaitForChild("TrackPieces")
	for index, pieceId in state.pieces do
		local variant = chooseVariant(pieceId, chain, origin)
		local template = templates:FindFirstChild(variant)
		if template then
			local m = template:Clone()
			m.Name = string.format("%02d_%s", index, variant)
			for _, p in m:GetDescendants() do
				if p:IsA("BasePart") then
					p.CFrame = chain * p.CFrame
					p.Anchored = true
				end
			end
			local pathFolder = m:FindFirstChild("Path")
			local exit = m:FindFirstChild("Exit") :: BasePart
			if pathFolder then
				-- path parts were already moved into world space above
				readPath(pathFolder, CFrame.identity, pieceId, path)
				pathFolder:Destroy()
			end
			chain = exit.CFrame
			exit:Destroy()
			m.Parent = trackFolder
		end
	end
	-- finish arch at the end of the track
	local arch = Instance.new("Model")
	arch.Name = "Finish"
	for _, side in { -1, 1 } do
		local post = Instance.new("Part")
		post.Anchored = true
		post.Size = Vector3.new(1.6, 14, 1.6)
		post.CFrame = chain * CFrame.new(side * 9.5, 7, 0)
		post.Color = Color3.fromRGB(43, 43, 51)
		post.Parent = arch
	end
	local top = Instance.new("Part")
	top.Anchored = true
	top.Size = Vector3.new(21, 3, 2)
	top.CFrame = chain * CFrame.new(0, 14.5, 0)
	top.Color = Color3.fromRGB(255, 255, 255)
	top.Material = Enum.Material.Neon
	top.Parent = arch
	arch.Parent = trackFolder

	state.path = path
	state.lengths = {}
	for i = 1, #path - 1 do
		state.lengths[i] = (path[i + 1].cf.Position - path[i].cf.Position).Magnitude
	end
	state.seg = 1
	state.dist = 0
end

local function spawnCar(state: State, carId: string)
	if state.car then
		state.car:Destroy()
		state.car = nil
	end
	local template = Assets:WaitForChild("Cars"):FindFirstChild(carId)
		or Assets.Cars:FindFirstChild("Buggy")
	local car = template:Clone() :: Model
	car.PrimaryPart = car:FindFirstChild("Root") :: BasePart
	for _, p in car:GetDescendants() do
		if p:IsA("BasePart") then
			p.Anchored = true
			p.CanCollide = false
			p.CanQuery = false
			p.CanTouch = false
		end
	end
	car.Name = "Car"
	car.Parent = state.plot
	state.car = car
	if state.path[1] then
		car:PivotTo(state.path[1].cf * CAR_OFFSET)
	end
end

function TrackService.setEarnHandler(fn: (Player, string, Vector3) -> ())
	onEarn = fn
end

-- (Re)builds the track if the piece list changed. Returns true if rebuilt.
function TrackService.refresh(player: Player, data, force: boolean?)
	local plot = PlotService.get(player)
	if not plot then
		return false
	end
	local pieces = Stats.trackPieces(data)
	local state = states[player]
	if state and not force then
		local same = #state.pieces == #pieces
		if same then
			for i, id in pieces do
				if state.pieces[i] ~= id then
					same = false
					break
				end
			end
		end
		if same then
			return false
		end
	end
	if not state then
		state = {
			player = player,
			plot = plot,
			pieces = pieces,
			path = {},
			lengths = {},
			car = nil,
			seg = 1,
			dist = 0,
		}
		states[player] = state
	end
	state.pieces = pieces
	buildPath(state)
	spawnCar(state, data.EquippedCar)
	return true
end

function TrackService.setCar(player: Player, carId: string)
	local state = states[player]
	if state then
		spawnCar(state, carId)
	end
end

function TrackService.clear(player: Player)
	local state = states[player]
	if not state then
		return
	end
	if state.car then
		state.car:Destroy()
	end
	local trackFolder = state.plot:FindFirstChild("Track")
	if trackFolder then
		trackFolder:ClearAllChildren()
	end
	states[player] = nil
end

function TrackService.start(getData: (Player) -> any)
	RunService.Heartbeat:Connect(function(dt)
		for player, state in states do
			local data = getData(player)
			local car = state.car
			local path = state.path
			if not data or not car or #path < 2 then
				continue
			end
			local remaining = Stats.carSpeed(data) * dt * (path[state.seg].boost or 1)
			local guard = 0
			while remaining > 0 and guard < 200 do
				guard += 1
				local a = path[state.seg]
				local b = path[state.seg + 1]
				if not b then
					state.seg = 1 -- lap finished: back to the start gate
					state.dist = 0
					break
				end
				if a.teleport then
					state.seg += 1
					state.dist = 0
					continue
				end
				local len = state.lengths[state.seg]
				if state.dist + remaining < len then
					state.dist += remaining
					remaining = 0
				else
					remaining -= (len - state.dist)
					state.seg += 1
					state.dist = 0
					if b.pieceEnd and onEarn then
						onEarn(player, b.pieceEnd, b.cf.Position)
					end
				end
			end
			local a = path[state.seg]
			local b = path[state.seg + 1] or a
			local len = state.lengths[state.seg] or 1
			local alpha = if len > 0 then math.clamp(state.dist / len, 0, 1) else 0
			car:PivotTo(a.cf:Lerp(b.cf, alpha) * CAR_OFFSET)
		end
	end)
end

return TrackService

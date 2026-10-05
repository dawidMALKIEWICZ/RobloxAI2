-- Places track tiles on each plot's grid, works out the drivable route from the start line and
-- drives the player's mini car along it.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Stats = require(ReplicatedStorage.Shared.Stats)
local PlotService = require(script.Parent.PlotService)

local Assets = ReplicatedStorage:WaitForChild("Assets")
local TilesFolder = Assets:WaitForChild("Tiles")

local TrackService = {}

type Waypoint = { cf: CFrame, teleport: boolean, boost: number, pieceEnd: string?, mult: number? }
type State = {
	player: Player,
	plot: Model,
	path: { Waypoint },
	lengths: { number },
	car: Model?,
	seg: number,
	dist: number,
	income: number,
	baseIncome: number,
}

local states: { [Player]: State } = {}
local onEarn: ((Player, string, Vector3, number) -> ())? = nil
local CAR_OFFSET = CFrame.new(0, 0.05, 0)

-- local waypoint data of every tile, read once from the templates (A -> B order)
local tileWaypoints: { [string]: { { cf: CFrame, teleport: boolean, boost: number } } } = {}
for _, tile in TilesFolder:GetChildren() do
	local list = {}
	local folder = tile:FindFirstChild("Path")
	if folder then
		local wps = folder:GetChildren()
		table.sort(wps, function(a, b)
			return tonumber(a.Name) < tonumber(b.Name)
		end)
		for _, wp in wps do
			table.insert(list, {
				cf = (wp :: BasePart).CFrame,
				teleport = wp:GetAttribute("Teleport") == true,
				boost = wp:GetAttribute("Boost") or 1,
			})
		end
	end
	tileWaypoints[tile.Name] = list
end

local function tileName(x: number, z: number, f: number?): string
	local floor = f or 0
	return if floor == 0 then "T_" .. x .. "_" .. z else "T_" .. x .. "_" .. z .. "_" .. floor
end
TrackService.tileName = tileName

-- recolours a tile model for its mutation (palette texture swap + glow colour)
function TrackService.applyMutation(model: Instance, mut: string?)
	local info = mut and Stats.Mutations[mut]
	if not info then
		return
	end
	model:SetAttribute("Mutation", mut)
	local glow = Color3.fromHex(if info.glow then info.glow else "#ffffff")
	for _, p in model:GetDescendants() do
		if p:IsA("MeshPart") then
			if p.Material == Enum.Material.Neon then
				p.Color = glow
			elseif p.TextureID ~= "" and info.texture then
				p.TextureID = info.texture
			end
		end
	end
end

-- builds the 3D model of one tile on the plot
function TrackService.spawnTile(plot: Model, x: number, z: number, r: number, id: string, f: number?,
	mut: string?, born: number?)
	local template = TilesFolder:FindFirstChild(id)
	if not template then
		return
	end
	local folder = plot:FindFirstChild("Track") :: Folder
	local old = folder:FindFirstChild(tileName(x, z, f))
	if old then
		old:Destroy()
	end
	local m = template:Clone()
	local path = m:FindFirstChild("Path")
	if path then
		path:Destroy()
	end
	local cf = PlotService.cellCFrame(plot, x, z, r, f)
	for _, p in m:GetDescendants() do
		if p:IsA("BasePart") then
			p.CFrame = cf * p.CFrame
			p.Anchored = true
		end
	end
	m.WorldPivot = cf
	m.Name = tileName(x, z, f)
	m:SetAttribute("PieceId", id)
	m:SetAttribute("Floor", f or 0)
	m:SetAttribute("Born", born or 0)
	TrackService.applyMutation(m, mut)
	m.Parent = folder
end

function TrackService.removeTile(plot: Model, x: number, z: number, f: number?)
	local folder = plot:FindFirstChild("Track") :: Folder
	local old = folder:FindFirstChild(tileName(x, z, f))
	if old then
		old:Destroy()
	end
end

local function buildPath(state: State, data)
	local steps = Stats.tracePath(data)
	local path: { Waypoint } = {}
	local valueSum = 0
	for _, step in steps do
		local cf = PlotService.cellCFrame(state.plot, step.x, step.z, step.r, step.f)
		local mult = Stats.mutMult(step.m)
		local list = tileWaypoints[step.id] or {}
		local n = #list
		local first = if #path == 0 then 1 else 2 -- waypoint 1 sits on the previous tile's exit
		for k = first, n do
			local src = if step.forward then list[k] else list[n - k + 1]
			local w = src.cf
			if not step.forward then
				w = w * CFrame.Angles(0, math.pi, 0) -- drive the tile backwards
			end
			local teleport = src.teleport
			if not step.forward then
				-- the teleport flag sits on the waypoint before the jump in A->B order
				local nextSrc = list[n - k]
				teleport = nextSrc ~= nil and nextSrc.teleport
			end
			table.insert(path, {
				cf = cf * w,
				teleport = teleport,
				boost = src.boost,
				pieceEnd = if k == n and step.id ~= "Start" then step.id else nil,
				mult = mult,
			})
		end
		local piece = Stats.Pieces[step.id]
		if piece then
			valueSum += piece.value * mult
		end
	end
	state.path = path
	state.lengths = {}
	local total = 0
	for i = 1, #path - 1 do
		local len = if path[i].teleport then 0 else (path[i + 1].cf.Position - path[i].cf.Position).Magnitude
		state.lengths[i] = len
		total += len
	end
	if state.seg > #path - 1 then
		state.seg = 1
		state.dist = 0
	end
	-- money per second for one lap, before multipliers (base = without speed potions)
	local lapTime = math.max(total / math.max(Stats.carSpeed(data), 1), 0.5) + 0.5
	local baseLap = math.max(total / math.max(Stats.carSpeed(data, true), 1), 0.5) + 0.5
	state.income = valueSum / lapTime
	state.baseIncome = valueSum / baseLap
end

local function spawnCar(state: State, carId: string)
	if state.car then
		state.car:Destroy()
		state.car = nil
	end
	local carsFolder = Assets:WaitForChild("Cars")
	local template = carsFolder:FindFirstChild(carId) or carsFolder:FindFirstChild("Buggy")
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
	car:SetAttribute("CarId", template.Name)
	car.Parent = state.plot
	state.car = car
	if state.path[1] then
		car:PivotTo(state.path[1].cf * CAR_OFFSET)
	end
end

function TrackService.setEarnHandler(fn: (Player, string, Vector3, number) -> ())
	onEarn = fn
end

-- builds every placed tile (on join) and the route
function TrackService.load(player: Player, data)
	local plot = PlotService.get(player)
	if not plot then
		return
	end
	(plot:FindFirstChild("Track") :: Folder):ClearAllChildren()
	local c = Stats.center()
	TrackService.spawnTile(plot, c, c, 0, "Start")
	for _, t in data.Placed do
		TrackService.spawnTile(plot, t.x, t.z, t.r, t.id, t.f, t.m)
	end
	PlotService.buildFloorFrame(plot, Stats.floors(data) >= 2)
	PlotService.syncPillars(plot, data.Placed)
	local state: State = {
		player = player,
		plot = plot,
		path = {},
		lengths = {},
		car = nil,
		seg = 1,
		dist = 0,
		income = 0,
		baseIncome = 0,
	}
	states[player] = state
	buildPath(state, data)
	spawnCar(state, data.EquippedCar)
end

function TrackService.refreshPath(player: Player, data)
	local state = states[player]
	if state then
		buildPath(state, data)
	end
end

function TrackService.income(player: Player, base: boolean?): number
	local state = states[player]
	if not state then
		return 0
	end
	return if base then state.baseIncome else state.income
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
	local folder = state.plot:FindFirstChild("Track")
	if folder then
		folder:ClearAllChildren()
	end
	local pillars = state.plot:FindFirstChild("Pillars")
	if pillars then
		pillars:ClearAllChildren()
	end
	PlotService.buildFloorFrame(state.plot, false)
	states[player] = nil
end

function TrackService.start(getData: (Player) -> any)
	RunService.Heartbeat:Connect(function(dt)
		for player, state in states do
			local data = getData(player)
			local car = state.car
			local path = state.path
			if not data or not car then
				continue
			end
			if #path < 2 then
				continue
			end
			local remaining = Stats.carSpeed(data) * dt * (path[state.seg].boost or 1)
			local guard = 0
			while remaining > 0 and guard < 200 do
				guard += 1
				local a = path[state.seg]
				local b = path[state.seg + 1]
				if not b then
					state.seg = 1 -- end of the road: back to the start line
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
						onEarn(player, b.pieceEnd, b.cf.Position, b.mult or 1)
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

-- Plot ownership, the build pad, island styles, owner signs and teleports.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local Stats = require(ReplicatedStorage.Shared.Stats)

local Assets = ReplicatedStorage:WaitForChild("Assets")
local Map = Workspace:WaitForChild("Map")
local PlotsFolder = Map:WaitForChild("Plots")

local PlotService = {}

local CELL = Stats.Config.Cell
local PAD_Y = 0.3 -- top of the build pad above the island grass

local owners: { [Model]: Player } = {}
local byPlayer: { [Player]: Model } = {}

local function sortedPlots(): { Model }
	local list = PlotsFolder:GetChildren()
	table.sort(list, function(a, b)
		return (a:GetAttribute("PlotIndex") or 0) < (b:GetAttribute("PlotIndex") or 0)
	end)
	return list
end

function PlotService.plotCFrame(plot: Model): CFrame
	local pivot = plot:FindFirstChild("Pivot") :: BasePart
	return pivot.CFrame * CFrame.new(0, -0.5, 0)
end

-- CFrame of a grid cell centre (on top of the pad, or of the second floor when f = 1),
-- rotated r quarter turns clockwise
function PlotService.cellCFrame(plot: Model, x: number, z: number, r: number?, f: number?): CFrame
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local c = Stats.center()
	return origin * CFrame.new((x - c) * CELL, PAD_Y + (f or 0) * Stats.FLOOR_H, (z - c) * CELL)
		* CFrame.Angles(0, -(r or 0) * math.pi / 2, 0)
end

-- ------------------------------------------------------------------ second floor
local STEEL = Color3.fromHex("#d9dee8")
local STEEL_DARK = Color3.fromHex("#8d96a8")

local function accentColor(plot: Model): Color3
	local hex = plot:GetAttribute("PlotColor")
	return if type(hex) == "string" then Color3.fromHex(hex) else Color3.fromHex("#3bb8ff")
end

local function structPart(name: string, size: Vector3, cf: CFrame, color: Color3, parent: Instance,
	material: Enum.Material?): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Size = size
	p.CFrame = cf
	p.Color = color
	p.Material = material or Enum.Material.SmoothPlastic
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Parent = parent
	return p
end

-- The frame of the second floor: four towers on the corners of the whole grid joined by
-- girders at floor height. `born` (server time) lets clients play the construction.
function PlotService.buildFloorFrame(plot: Model, on: boolean, born: number?)
	local old = plot:FindFirstChild("FloorFrame")
	if old then
		old:Destroy()
	end
	if not on then
		return
	end
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local frame = Instance.new("Model")
	frame.Name = "FloorFrame"
	frame:SetAttribute("Born", born or 0)
	local half = Stats.Config.MaxGrid * CELL / 2 + 1.5
	local top = PAD_Y + Stats.FLOOR_H
	local accent = accentColor(plot)
	for i, corner in { { -1, -1 }, { 1, -1 }, { 1, 1 }, { -1, 1 } } do
		local x, z = corner[1] * half, corner[2] * half
		local tower = Instance.new("Model")
		tower.Name = "Tower" .. i
		tower:SetAttribute("Order", i)
		local h = top + 3
		structPart("Column", Vector3.new(2.2, h, 2.2), origin * CFrame.new(x, h / 2, z), STEEL, tower)
		structPart("Foot", Vector3.new(3.6, 0.8, 3.6), origin * CFrame.new(x, 0.4, z), STEEL_DARK, tower)
		structPart("Band", Vector3.new(2.5, 0.5, 2.5), origin * CFrame.new(x, top, z), accent, tower)
		structPart("Cap", Vector3.new(3, 0.6, 3), origin * CFrame.new(x, h + 0.3, z), STEEL_DARK, tower)
		local beacon = structPart("Beacon", Vector3.new(1.3, 1.3, 1.3), origin * CFrame.new(x, h + 1.25, z),
			accent, tower, Enum.Material.Neon)
		beacon.Shape = Enum.PartType.Ball
		local light = Instance.new("PointLight")
		light.Color = accent
		light.Range = 16
		light.Brightness = 1.4
		light.Parent = beacon
		tower.Parent = frame
	end
	-- girders along the four edges, with a glowing trim on the outside
	for i, e in { { 0, -1 }, { 1, 0 }, { 0, 1 }, { -1, 0 } } do
		local along = e[1] == 0
		local len = half * 2 - 2.2
		local cf = origin * CFrame.new(e[1] * half, top - 0.45, e[2] * half)
		local girder = Instance.new("Model")
		girder.Name = "Girder" .. i
		girder:SetAttribute("Order", i)
		structPart("Beam", if along then Vector3.new(len, 0.9, 0.9) else Vector3.new(0.9, 0.9, len), cf,
			STEEL, girder)
		structPart("Trim", if along then Vector3.new(len, 0.18, 0.2) else Vector3.new(0.2, 0.18, len),
			cf * CFrame.new(e[1] * 0.5, 0, e[2] * 0.5), accent, girder, Enum.Material.Neon)
		girder.Parent = frame
	end
	frame.Parent = plot
end

-- Pillars under the second floor: one per grid corner touching a floor-2 tile, plus edge
-- beams under every floor-2 tile. New pieces get a Born time so clients can grow them.
function PlotService.syncPillars(plot: Model, placed: { any }, born: number?)
	local folder = plot:FindFirstChild("Pillars")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "Pillars"
		folder.Parent = plot
	end
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local c = Stats.center()
	local want = {}
	for _, t in placed do
		if (t.f or 0) == 1 then
			for _, k in { { 0, 0 }, { 1, 0 }, { 0, 1 }, { 1, 1 } } do
				want["P_" .. (t.x + k[1]) .. "_" .. (t.z + k[2])] = { kind = "P", x = t.x + k[1], z = t.z + k[2] }
			end
			-- H_<cell x>_<grid line z> runs along x, V_<grid line x>_<cell z> runs along z
			for _, l in { t.z, t.z + 1 } do
				want["H_" .. t.x .. "_" .. l] = { kind = "H", x = t.x, z = l }
			end
			for _, l in { t.x, t.x + 1 } do
				want["V_" .. l .. "_" .. t.z] = { kind = "V", x = l, z = t.z }
			end
		end
	end
	for _, child in folder:GetChildren() do
		if not want[child.Name] then
			child:Destroy()
		end
	end
	local top = PAD_Y + Stats.FLOOR_H
	local accent = accentColor(plot)
	for name, w in want do
		if folder:FindFirstChild(name) then
			continue
		end
		-- corner (x, z) of the grid = between cells x-1 and x
		local px = (w.x - c - 0.5) * CELL
		local pz = (w.z - c - 0.5) * CELL
		local p
		if w.kind == "P" then
			local h = top - 0.1
			p = structPart(name, Vector3.new(0.8, h, 0.8), origin * CFrame.new(px, h / 2, pz), STEEL, folder)
			structPart("Cap", Vector3.new(1.25, 0.35, 1.25), origin * CFrame.new(px, top - 0.3, pz), accent, p)
			structPart("Foot", Vector3.new(1.3, 0.3, 1.3), origin * CFrame.new(px, 0.15, pz), STEEL_DARK, p)
		elseif w.kind == "H" then
			-- beam along x on grid line z, under cell column x
			p = structPart(name, Vector3.new(CELL - 0.8, 0.45, 0.4),
				origin * CFrame.new((w.x - c) * CELL, top - 0.35, pz), STEEL_DARK, folder)
		else
			p = structPart(name, Vector3.new(0.4, 0.45, CELL - 0.8),
				origin * CFrame.new(px, top - 0.35, (w.z - c) * CELL), STEEL_DARK, folder)
		end
		p:SetAttribute("Born", born or 0)
		p:SetAttribute("Kind", w.kind)
	end
end

function PlotService.spawnCFrame(plot: Model): CFrame
	local sp = plot:FindFirstChild("SpawnPoint") :: BasePart
	return sp.CFrame * CFrame.new(0, 3, 0) * CFrame.Angles(0, math.pi, 0)
end

local function setSign(plot: Model, text: string)
	local sign = plot:FindFirstChild("OwnerSign")
	local gui = sign and sign:FindFirstChild("Sign")
	local lbl = gui and gui:FindFirstChild("Text")
	if lbl then
		(lbl :: TextLabel).Text = text
	end
end

function PlotService.get(player: Player): Model?
	return byPlayer[player]
end

function PlotService.claim(player: Player): Model?
	if byPlayer[player] then
		return byPlayer[player]
	end
	for _, plot in sortedPlots() do
		if not owners[plot] then
			owners[plot] = player
			byPlayer[player] = plot
			plot:SetAttribute("OwnerId", player.UserId)
			setSign(plot, player.DisplayName .. "'s Plot")
			return plot
		end
	end
	return nil
end

function PlotService.release(player: Player)
	local plot = byPlayer[player]
	if not plot then
		return
	end
	owners[plot] = nil
	byPlayer[player] = nil
	plot:SetAttribute("OwnerId", nil)
	setSign(plot, "Empty Plot " .. tostring(plot:GetAttribute("PlotIndex")))
	PlotService.applyStyle(plot, "Classic")
	PlotService.buildPad(plot, Stats.Config.BaseGrid)
end

-- The light build pad with grid lines covering the unlocked cells.
function PlotService.buildPad(plot: Model, size: number)
	local pad = plot:FindFirstChild("Pad") :: Folder
	pad:ClearAllChildren()
	plot:SetAttribute("GridSize", size)
	local half = size * CELL / 2
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local slab = Instance.new("Part")
	slab.Name = "Slab"
	slab.Anchored = true
	slab.Size = Vector3.new(size * CELL, 0.3, size * CELL)
	slab.CFrame = origin * CFrame.new(0, PAD_Y - 0.15, 0)
	slab.Color = Color3.fromHex("#b8f08f")
	slab.Material = Enum.Material.SmoothPlastic
	slab.TopSurface = Enum.SurfaceType.Smooth
	slab.Parent = pad
	for i = 0, size do
		local off = -half + i * CELL
		for _, horizontal in { true, false } do
			local line = Instance.new("Part")
			line.Name = "Line"
			line.Anchored = true
			line.CanCollide = false
			line.CanQuery = false
			line.Size = if horizontal then Vector3.new(size * CELL, 0.06, 0.25)
				else Vector3.new(0.25, 0.06, size * CELL)
			line.CFrame = origin * (if horizontal then CFrame.new(0, PAD_Y + 0.02, off)
				else CFrame.new(off, PAD_Y + 0.02, 0))
			line.Color = Color3.fromHex("#8fd36a")
			line.Material = Enum.Material.SmoothPlastic
			line.Parent = pad
		end
	end
	-- Keep the build pad open: no corner posts.

end

function PlotService.teleport(player: Player, target: string?)
	local char = player.Character
	if not char or not char.PrimaryPart then
		return
	end
	if target == "Cars" or target == "Styles" then
		local shop = Map:FindFirstChild("Hub") and Map.Hub:FindFirstChild("Shop_" .. target)
		local tp = shop and shop:FindFirstChild("TP_" .. target) :: BasePart?
		if tp then
			char:PivotTo(tp.CFrame * CFrame.new(0, 3, 0))
		end
		return
	end
	local plot = byPlayer[player]
	if plot then
		char:PivotTo(PlotService.spawnCFrame(plot))
	end
end

-- Recolours the island and swaps its decoration for the chosen style.
function PlotService.applyStyle(plot: Model, styleId: string)
	local styleFolder = Assets:WaitForChild("IslandStyles")
	local style = styleFolder:FindFirstChild(styleId) or styleFolder:FindFirstChild("Classic")
	if not style then
		return
	end
	local island = plot:FindFirstChild("Island")
	local function recolor(p: Instance)
		if p:IsA("BasePart") then
			local role = p:GetAttribute("Role")
			if role == "Grass" or role == "Dirt" or role == "Rock" then
				p.Color = Color3.fromHex(style:GetAttribute(role .. "Color"))
				p.Material = Enum.Material.SmoothPlastic
			end
		end
	end
	if island then
		for _, p in island:GetDescendants() do
			recolor(p)
		end
	end
	local gridArea = plot:FindFirstChild("GridArea") :: BasePart?
	if gridArea then
		recolor(gridArea)
		local h, s, v = gridArea.Color:ToHSV()
		gridArea.Color = Color3.fromHSV(h, s, v * 0.85)
	end
	local old = plot:FindFirstChild("Decor")
	if old then
		old:Destroy()
	end
	local decor = (style:FindFirstChild("Decor") :: Model):Clone()
	local base = PlotService.plotCFrame(plot)
	for _, p in decor:GetDescendants() do
		if p:IsA("BasePart") then
			p.CFrame = base * p.CFrame
			p.Anchored = true
		end
	end
	decor.Name = "Decor"
	decor.Parent = plot
	plot:SetAttribute("Style", style.Name)
end

function PlotService.start()
	for _, plot in sortedPlots() do
		PlotService.buildPad(plot, Stats.Config.BaseGrid)
	end
	local catcher = Map:FindFirstChild("VoidCatcher") :: BasePart?
	if catcher then
		catcher.Touched:Connect(function(hit)
			local char = hit:FindFirstAncestorOfClass("Model")
			local player = char and Players:GetPlayerFromCharacter(char)
			if player and char then
				local plot = byPlayer[player]
				if plot then
					char:PivotTo(PlotService.spawnCFrame(plot))
				else
					char:PivotTo(CFrame.new(0, 110, 16))
				end
			end
		end)
	end
end

return PlotService


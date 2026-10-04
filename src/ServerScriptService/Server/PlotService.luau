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

-- CFrame of a grid cell centre (on top of the pad), rotated r quarter turns clockwise
function PlotService.cellCFrame(plot: Model, x: number, z: number, r: number?): CFrame
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local c = Stats.center()
	return origin * CFrame.new((x - c) * CELL, PAD_Y, (z - c) * CELL)
		* CFrame.Angles(0, -(r or 0) * math.pi / 2, 0)
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


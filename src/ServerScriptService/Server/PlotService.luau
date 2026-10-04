-- Plot ownership, island styles, owner signs and teleporting players to their island.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local Assets = ReplicatedStorage:WaitForChild("Assets")
local Map = Workspace:WaitForChild("Map")
local PlotsFolder = Map:WaitForChild("Plots")

local PlotService = {}

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

function PlotService.spawnCFrame(plot: Model): CFrame
	local sp = plot:FindFirstChild("SpawnPoint") :: BasePart
	-- face into the plot (away from the hub)
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

function PlotService.ownerOf(plot: Model): Player?
	return owners[plot]
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
end

function PlotService.teleport(player: Player)
	local plot = byPlayer[player]
	local char = player.Character
	if plot and char and char.PrimaryPart then
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
	if island then
		for _, p in island:GetDescendants() do
			if p:IsA("BasePart") then
				local role = p:GetAttribute("Role")
				if role == "Grass" or role == "Dirt" or role == "Rock" then
					p.Color = Color3.fromHex(style:GetAttribute(role .. "Color"))
					local ok, mat = pcall(function()
						return (Enum.Material :: any)[style:GetAttribute(role .. "Material")]
					end)
					if ok and mat then
						p.Material = mat
					end
				end
			end
		end
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
	-- void catcher: anyone falling off is sent back to their island (or the hub)
	local catcher = Map:FindFirstChild("VoidCatcher") :: BasePart?
	if catcher then
		catcher.Touched:Connect(function(hit)
			local char = hit:FindFirstAncestorOfClass("Model")
			local player = char and Players:GetPlayerFromCharacter(char)
			if player then
				local plot = byPlayer[player]
				if plot then
					char:PivotTo(PlotService.spawnCFrame(plot))
				else
					char:PivotTo(CFrame.new(0, 110, 14))
				end
			end
		end)
	end
end

return PlotService

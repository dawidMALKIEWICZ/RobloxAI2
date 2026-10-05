-- Connects the pre-built MainGui (StarterGui) to the server: HUD values, windows, the roll reel
-- and build mode (blueprint placing on your plot). The UI itself is built in StarterGui.
local Players = game:GetService("Players")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local Workspace = game:GetService("Workspace")

local GameData = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameData"))
local Stats = require(ReplicatedStorage.Shared:WaitForChild("Stats"))
local Format = require(ReplicatedStorage.Shared:WaitForChild("Format"))
local Remotes = ReplicatedStorage:WaitForChild("Remotes")
local Assets = ReplicatedStorage:WaitForChild("Assets")
local Tiles = Assets:WaitForChild("Tiles")

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("MainGui")
local root = gui:WaitForChild("Root")
local UIIconAtlas = require(ReplicatedStorage:WaitForChild("UIIconAtlas"))
UIIconAtlas.Apply(gui)
gui:GetAttributeChangedSignal("IconAtlas"):Connect(function()
	UIIconAtlas.Apply(gui)
end)
local hud = root:WaitForChild("HUD")
local windows = root:WaitForChild("Windows")
local buildPanel = root:WaitForChild("BuildPanel")
local reel = root:WaitForChild("RollReel")
local toasts = root:WaitForChild("Toasts")
local templates = root:WaitForChild("Templates")
local UIVisuals = require(ReplicatedStorage:WaitForChild("UIVisuals"))
UIVisuals.Bind(gui)
local vfx = require(ReplicatedStorage:WaitForChild("ClientVFX")).new(gui)
local worldFX = require(ReplicatedStorage:WaitForChild("WorldFX")).new(gui)
vfx.WorldFX = worldFX
local uiFX = require(ReplicatedStorage:WaitForChild("UIFX")).new(gui, GameData)
local Mutations = require(ReplicatedStorage:WaitForChild("Mutations"))
task.spawn(Mutations.startWorld, Workspace:WaitForChild("Map"))

local snap = nil
local snapTime = 0
local busy = false
local lastRollClock = -100

-- ------------------------------------------------------------------ colour presets
local function seq(lt, base, dk)
	return ColorSequence.new({
		ColorSequenceKeypoint.new(0, Color3.fromHex(lt)),
		ColorSequenceKeypoint.new(0.42, Color3.fromHex(base)),
		ColorSequenceKeypoint.new(0.58, Color3.fromHex(base)),
		ColorSequenceKeypoint.new(1, Color3.fromHex(dk)),
	})
end
local PRESET = {
	green = seq("#c9ff7a", "#62e026", "#2c9c10"),
	red = seq("#ff9aa5", "#ff3d5e", "#c3112f"),
	gray = seq("#eeeeee", "#a9a9b3", "#6d6d78"),
	blue = seq("#a6e9ff", "#33aaff", "#1563c9"),
	yellow = seq("#fff59a", "#ffc61a", "#e58a00"),
	purple = seq("#e6b8ff", "#a64dff", "#6a1fc9"),
}

local function setPreset(button: Instance, preset: string)
	local g = button:FindFirstChild("Gradient")
	if g then
		(g :: UIGradient).Color = PRESET[preset]
	end
end

local function setText(button: Instance, text: string)
	local lbl = button:FindFirstChild("Label")
	if lbl then
		(lbl :: TextLabel).Text = text
	end
end

local function tierColor(tier: string): Color3
	if tier == "Secret" then
		return Color3.new(1, 1, 1)
	end
	return Color3.fromHex(Stats.Tiers[tier].color)
end

-- ------------------------------------------------------------------ scaling
local scale = root:WaitForChild("Scale") :: UIScale
local function rescale()
	local cam = Workspace.CurrentCamera
	if not cam then
		return
	end
	local vp = cam.ViewportSize
	local s = math.max(math.min(vp.X / 1920, vp.Y / 1080), 0.3)
	scale.Scale = s
	root.Size = UDim2.fromOffset(vp.X / s, vp.Y / s)
end
rescale()
Workspace:GetPropertyChangedSignal("CurrentCamera"):Connect(rescale)
if Workspace.CurrentCamera then
	Workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(rescale)
end

-- ------------------------------------------------------------------ helpers
local function request(action: string, arg: any?)
	-- keep a copy of a tile that is about to be removed so it can shrink away nicely
	local removed: Model? = nil
	if action == "Remove" and type(arg) == "table" then
		for _, plot in Workspace.Map.Plots:GetChildren() do
			if plot:GetAttribute("OwnerId") == player.UserId then
				local f = tonumber(arg.f) or 0
				local name = "T_" .. tostring(arg.x) .. "_" .. tostring(arg.z) .. (if f ~= 0 then "_" .. f else "")
				local tile = plot.Track:FindFirstChild(name)
				if tile then
					removed = tile:Clone()
				end
			end
		end
	end
	local ok, a, b, c = pcall(function()
		return Remotes.Request:InvokeServer(action, arg)
	end)
	if not ok then
		return false, "Connection error"
	end
	if a == true and removed then
		worldFX:RemoveGhost(removed)
	end
	if a == true then
		if action == "BuyPotion" and Stats.Potions[arg] then
			vfx:Potion(Stats.Potions[arg])
		elseif action:match("^Buy") or action:match("^Claim") then
			vfx:Purchase(action == "BuyUpgrade" and "Upgrade" or "Purchase")
		elseif action == "Remove" and type(arg) == "table" then
			for _,plot in Workspace.Map.Plots:GetChildren() do
				if plot:GetAttribute("OwnerId") == player.UserId then
					local center=Stats.center()
					local y=.3+(tonumber(arg.f) or 0)*Stats.FLOOR_H
					local pos=(plot.GridOrigin.CFrame*CFrame.new((arg.x-center)*Stats.Config.Cell,y,(arg.z-center)*Stats.Config.Cell)).Position
					vfx:Remove(pos)
					break
				end
			end
		end
	elseif a == false and action ~= "GetData" and not (action == "Roll" and arg == "auto") then vfx:Error(vfx.LastButton) end
	return a, b, c
end

local toastOrder = 0
local function toast(text: string, color: string?)
	local t = templates:WaitForChild("Toast"):Clone()
	local lbl = t:FindFirstChild("Text") :: TextLabel
	lbl.Text = text
	lbl.TextColor3 = Color3.fromHex(color or "#ffffff")
	toastOrder += 1
	t.LayoutOrder = toastOrder
	t.Visible = true
	t.Parent = toasts
	vfx:Toast(t)
	task.delay(3, function()
		TweenService:Create(lbl, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
		TweenService:Create(t, TweenInfo.new(0.4), { BackgroundTransparency = 1 }):Play()
		task.wait(0.45)
		t:Destroy()
	end)
	local frames = {}
	for _, c in toasts:GetChildren() do
		if c:IsA("Frame") then
			table.insert(frames, c)
		end
	end
	if #frames > 4 then
		table.sort(frames, function(a, b)
			return a.LayoutOrder < b.LayoutOrder
		end)
		frames[1]:Destroy()
	end
end

local function result(ok, msg)
	if msg then
		toast(msg, if ok then "#9dff7a" else "#ff8a96")
	end
end

local function bounce(button: GuiButton)
	vfx:BindButton(button)
end
for _, d in root:GetDescendants() do
	if d:IsA("GuiButton") and not d:IsDescendantOf(templates) then
		bounce(d)
	end
end

local function onClick(button: Instance?, fn: () -> ())
	if button and button:IsA("GuiButton") then
		button.Activated:Connect(fn)
	end
end

-- puts a 3D model in a ViewportFrame with a camera looking at it
local function showInViewport(vp: ViewportFrame, model: Model, dist: number?)
	for _, c in vp:GetChildren() do
		if c:IsA("Model") or c:IsA("Camera") then
			c:Destroy()
		end
	end
	local clone = model:Clone()
	local path = clone:FindFirstChild("Path")
	if path then
		path:Destroy()
	end
	clone.Parent = vp
	local cf, size = clone:GetBoundingBox()
	local d = dist or (size.Magnitude * 1.1 + 2)
	local cam = Instance.new("Camera")
	cam.FieldOfView = 40
	cam.CFrame = CFrame.lookAt(cf.Position + Vector3.new(d * 0.55, d * 0.6, d * 0.65), cf.Position)
	cam.Parent = vp
	vp.CurrentCamera = cam
end

-- ------------------------------------------------------------------ windows
local openWindow: GuiObject? = nil
local closeBuild -- forward

local function closeWindows()
	for _, w in windows:GetChildren() do
		if w:IsA("GuiObject") then
			w.Visible = false
		end
	end
	openWindow = nil
end

local function open(name: string)
	local w = windows:FindFirstChild(name) :: GuiObject
	if not w then
		return
	end
	if openWindow == w then
		closeWindows()
		return
	end
	closeWindows()
	closeBuild()
	w.Visible = true
	openWindow = w
	if name == "SkillsWindow" then
		return
	end
	-- ClientVFX animates the window and staggers its cards.
end

for _, w in windows:GetChildren() do
	local header = w:FindFirstChild("Header")
	onClick(header and header:FindFirstChild("Close"), closeWindows)
end

-- dice fusion, offline popup and the second floor (see ReplicatedStorage.Systems)
local systems = require(ReplicatedStorage:WaitForChild("Systems")).new({
	gui = gui, vfx = vfx, worldFX = worldFX, uiFX = uiFX, request = request, toast = toast,
	setPreset = setPreset, setText = setText, open = open, closeWindows = closeWindows,
})
Remotes:WaitForChild("Offline").OnClientEvent:Connect(function(info)
	systems:ShowOffline(info)
end)

-- ------------------------------------------------------------------ centered roll reveal
local rollReveal = require(ReplicatedStorage:WaitForChild("RollReveal")).new(gui)
rollReveal.VFX = vfx
local function playReel(res, fast: boolean)
 rollReveal:Play(res, fast, snap and snap.RollTime or 2)
end

local rollArea = hud:WaitForChild("RollArea")
local rollButton = rollArea:WaitForChild("RollButton")

local function doRoll(auto: boolean?)
	if busy or not snap then
		return
	end
	if os.clock() - lastRollClock < snap.RollTime then
		return
	end
	if auto ~= true then rollReveal:Resume() end
	busy = true
	lastRollClock = os.clock()
	local ok, msg, res = request("Roll", if auto then "auto" else nil)
	busy = false
	if ok and res then
		task.spawn(playReel, res, auto == true)
	elseif msg and not auto then
		toast(msg, "#ff8a96")
	end
end

onClick(rollButton, function()
	doRoll(false)
end)
local function toggleAuto()
 if snap then
  result(request("SetAuto", not snap.Data.AutoRoll))
 end
end
onClick(rollArea:FindFirstChild("AutoButton"), toggleAuto)
rollReveal.OnAuto = toggleAuto
-- Further manual rolls are started with the HUD dice button.
for _, d in GameData.Dice do
	onClick(rollArea.DiceBar:FindFirstChild("Dice_" .. d.id), function()
		local ok, msg, res = request("UseDice", d.id)
		if ok and res then
			vfx:DiceRoll(d)
			rollReveal:Resume()
			task.spawn(playReel, res, false)
		else
			result(ok, msg)
		end
	end)
end
Remotes.Rolled.OnClientEvent:Connect(function(res)
	rollReveal:Resume()
	playReel(res, false)
end)

-- ------------------------------------------------------------------ build mode
local selected: string? = nil -- inventory key: "PieceId" or "PieceId@Mutation"
local rotation = 0
local deleteMode = false
local ghost: Model? = nil
local ghostHighlight: Highlight? = nil
local placedCache = {} -- Stats.placedMap of the latest snapshot (not rebuilt every frame)

-- the blueprint breathes so it reads clearly against the pad
RunService.RenderStepped:Connect(function()
	if ghostHighlight and ghostHighlight.Parent then
		local k = (math.sin(os.clock() * 5) + 1) / 2
		ghostHighlight.FillTransparency = 0.45 + k * 0.3
		ghostHighlight.OutlineTransparency = k * 0.4
	end
end)

local function myPlot(): Model?
	for _, plot in Workspace:WaitForChild("Map"):WaitForChild("Plots"):GetChildren() do
		if plot:GetAttribute("OwnerId") == player.UserId then
			return plot
		end
	end
	return nil
end

local function buildFloor(): number
	return systems.buildFloor
end

local function cellCFrame(plot: Model, x: number, z: number, r: number, f: number?): CFrame
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local c = Stats.center()
	local cell = Stats.Config.Cell
	return origin * CFrame.new((x - c) * cell, 0.3 + (f or 0) * Stats.FLOOR_H, (z - c) * cell)
		* CFrame.Angles(0, -r * math.pi / 2, 0)
end

local function clearGhost()
	if ghost then
		ghost:Destroy()
		ghost = nil
	end
	ghostHighlight = nil
end

local function makeGhost(key: string)
	clearGhost()
	local id, mut = Stats.splitKey(key)
	local template = Tiles:FindFirstChild(id)
	if not template then
		return
	end
	local g = template:Clone()
	local path = g:FindFirstChild("Path")
	if path then
		path:Destroy()
	end
	Mutations.apply(g, mut)
	for _, p in g:GetDescendants() do
		if p:IsA("BasePart") then
			p.Anchored = true
			p.CanCollide = false
			p.CanQuery = false
			p.CanTouch = false
			p.Transparency = math.max(p.Transparency, 0.35)
		end
	end
	local h = Instance.new("Highlight")
	h.FillTransparency = 0.6
	h.OutlineTransparency = 0
	h.Parent = g
	-- templates sit at the tile origin; pivot there so the blueprint lines up with the cell
	g.WorldPivot = CFrame.new()
	g.Name = "Blueprint"
	g.Parent = Workspace
	ghost = g
	ghostHighlight = h
end

local function makeDeleteGhost()
	clearGhost()
	local g = Instance.new("Model")
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.Size = Vector3.new(Stats.Config.Cell - 0.4, 3, Stats.Config.Cell - 0.4)
	p.Transparency = 0.6
	p.Color = Color3.fromHex("#ff3b5c")
	p.Material = Enum.Material.Neon
	p.Parent = g
	g.PrimaryPart = p
	g.Name = "DeleteMarker"
	g.Parent = Workspace
	ghost = g
end

local function setSelected(key: string?)
	selected = key
	deleteMode = false
	if key then
		makeGhost(key)
		local piece = Stats.Pieces[(Stats.splitKey(key))]
		if piece and piece.lift and buildFloor() ~= 0 then
			systems:SetBuildFloor(0) -- Sky Ramps always start on the ground floor
		end
	else
		clearGhost()
	end
	for _, item in buildPanel.Items:GetChildren() do
		if item:IsA("GuiButton") then
			local stroke = item:FindFirstChild("Stroke") :: UIStroke
			local pid = string.sub(item.Name, 6)
			local _, mut = Stats.splitKey(pid)
			stroke.Thickness = if pid == key then 4 else 3
			stroke.Color = if pid == key then Color3.fromRGB(40, 225, 255)
				elseif mut then Mutations.color(mut) else Color3.fromRGB(9, 14, 25)
		end
	end
	setPreset(buildPanel.DeleteButton, "red")
	setText(buildPanel.DeleteButton, "Delete")
end

function closeBuild()
	buildPanel.Visible = false
	worldFX:ShowRoute(nil, nil, false)
	setSelected(nil)
	deleteMode = false
	systems:SetBuildOpen(false)
end

local function openBuild()
	closeWindows()
	rollReveal:Cancel()
	-- Build only opens the menu; it never moves the character.
	buildPanel.Visible = true
	systems:SetBuildOpen(true)
	worldFX:ShowRoute(myPlot(), snap and snap.Data, true)
end

systems.OnFloorChanged = function()
	if deleteMode then
		makeDeleteGhost()
	end
end

onClick(rollArea:FindFirstChild("BuildButton"), function()
	if buildPanel.Visible then
		closeBuild()
	else
		openBuild()
	end
end)
onClick(buildPanel:FindFirstChild("Close"), closeBuild)
onClick(buildPanel:FindFirstChild("RotateButton"), function()
	rotation = (rotation + 1) % 4
end)
onClick(buildPanel:FindFirstChild("DeleteButton"), function()
	if deleteMode then
		setSelected(nil)
	else
		setSelected(nil)
		deleteMode = true
		makeDeleteGhost()
		setPreset(buildPanel.DeleteButton, "yellow")
		setText(buildPanel.DeleteButton, "Deleting")
	end
end)

local function wireItem(item: GuiButton, key: string)
	onClick(item, function()
		if not snap or (snap.Data.Inventory[key] or 0) <= 0 then
			local piece = Stats.Pieces[(Stats.splitKey(key))]
			toast("Roll the dice to get more " .. (if piece then piece.name else key) .. "!", "#ff8a96")
			return
		end
		setSelected(if selected == key then nil else key)
	end)
end
for _, pc in GameData.Pieces do
	local item = buildPanel.Items:FindFirstChild("Item_" .. pc.id)
	if item then
		item.LayoutOrder = pc.order * 10
		local tile = Tiles:FindFirstChild(pc.id)
		if tile then
			showInViewport(item:FindFirstChild("Viewport") :: ViewportFrame, tile, 15)
		end
		wireItem(item, pc.id)
	end
end

-- cards for mutated copies ("Golden Loop", ...) are cloned from the plain card on demand
local function variantCard(key: string): GuiButton?
	local card = buildPanel.Items:FindFirstChild("Item_" .. key)
	if card then
		return card
	end
	local id, mut = Stats.splitKey(key)
	local base = buildPanel.Items:FindFirstChild("Item_" .. id)
	local m = mut and Stats.Mutations[mut]
	if not base or not m then
		return nil
	end
	card = systems.freshClone(base)
	card.Name = "Item_" .. key
	card.LayoutOrder = base.LayoutOrder + m.order
	local tile = Tiles:FindFirstChild(id)
	local vp = card:FindFirstChild("Viewport")
	if tile and vp then
		local model = tile:Clone()
		Mutations.apply(model, mut)
		showInViewport(vp :: ViewportFrame, model, 15)
		model:Destroy()
	end
	Mutations.badge(card, mut)
	local name = card:FindFirstChild("Name")
	if name and name:IsA("TextLabel") then
		name.Text = m.name .. " " .. (Stats.Pieces[id] and Stats.Pieces[id].name or id)
	end
	local tier = card:FindFirstChild("Tier")
	if tier and tier:IsA("TextLabel") then
		tier.Text = "x" .. m.mult .. " money"
		tier.TextColor3 = Mutations.color(mut)
	end
	local stroke = card:FindFirstChild("Stroke")
	if stroke and stroke:IsA("UIStroke") then
		stroke.Color = Mutations.color(mut)
	end
	card.Parent = buildPanel.Items
	vfx:BindButton(card :: GuiButton)
	wireItem(card :: GuiButton, key)
	return card :: GuiButton
end

local function pointerCell(plot: Model, screenPos: Vector2)
	local cam = Workspace.CurrentCamera
	local ray = cam:ViewportPointToRay(screenPos.X, screenPos.Y)
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local planeY = origin.Position.Y + 0.3 + buildFloor() * Stats.FLOOR_H
	if math.abs(ray.Direction.Y) < 1e-4 then
		return nil
	end
	local t = (planeY - ray.Origin.Y) / ray.Direction.Y
	if t < 0 then
		return nil
	end
	local hit = ray.Origin + ray.Direction * t
	local loc = origin:PointToObjectSpace(hit)
	local c = Stats.center()
	local cell = Stats.Config.Cell
	local x = math.floor(loc.X / cell + 0.5) + c
	local z = math.floor(loc.Z / cell + 0.5) + c
	if x < 0 or z < 0 or x >= Stats.Config.MaxGrid or z >= Stats.Config.MaxGrid then
		return nil
	end
	return { x = x, z = z }
end

local function cellValid(x: number, z: number): boolean
	if not snap or not selected then
		return false
	end
	local data = snap.Data
	local id = Stats.splitKey(selected)
	return (data.Inventory[selected] or 0) > 0 and (Stats.canPlace(data, x, z, buildFloor(), id, placedCache))
end

RunService.RenderStepped:Connect(function(dt)
	if not ghost then
		return
	end
	local plot = myPlot()
	if not plot then
		return
	end
	local cell = pointerCell(plot, UserInputService:GetMouseLocation())
	if not cell then
		ghost:PivotTo(CFrame.new(0, -500, 0))
		return
	end
	if deleteMode then
		ghost:PivotTo(cellCFrame(plot, cell.x, cell.z, 0, buildFloor()) * CFrame.new(0, 1.5, 0))
		return
	end
	local target = cellCFrame(plot, cell.x, cell.z, rotation, buildFloor())
	if (ghost:GetPivot().Position-target.Position).Magnitude>45 then ghost:PivotTo(target)
	else ghost:PivotTo(ghost:GetPivot():Lerp(target,1-math.exp(-dt*26))) end
	if ghostHighlight then
		ghostHighlight.FillTransparency=.61+math.sin(os.clock()*5)*.045
		local ok = cellValid(cell.x, cell.z)
		ghostHighlight.FillColor = if ok then Color3.fromHex("#5fff6a") else Color3.fromHex("#ff3b5c")
		ghostHighlight.OutlineColor = ghostHighlight.FillColor
	end
end)

local function tryBuildAt(screenPos: Vector2)
	local plot = myPlot()
	if not plot or not ghost then
		return
	end
	local cell = pointerCell(plot, screenPos)
	if not cell then
		return
	end
	local f = buildFloor()
	if deleteMode then
		local ok, msg = request("Remove", { x = cell.x, z = cell.z, f = f })
		if not ok and msg then
			toast(msg, "#ff8a96")
		end
		return
	end
	if selected then
		local key = selected
		local ok, msg = request("Place", { x = cell.x, z = cell.z, r = rotation, id = key, f = f })
		if not ok and msg then
			toast(msg, "#ff8a96")
		elseif ok and snap and (snap.Data.Inventory[key] or 0) <= 0 then
			setSelected(nil)
		end
	end
end

-- touch: only a quick tap builds (dragging or pinching the camera never places or deletes)
local touchStart: { [InputObject]: { pos: Vector2, t: number } } = {}
UserInputService.InputBegan:Connect(function(input, processed)
	if input.KeyCode == Enum.KeyCode.R and not processed then
		rotation = (rotation + 1) % 4
		if ghost then vfx:Sound("Click",1.15,.28) end
	elseif input.KeyCode == Enum.KeyCode.F and not processed and buildPanel.Visible then
		if snap and Stats.floors(snap.Data) >= 2 then
			systems:FloorClicked()
		end
	elseif (input.KeyCode == Enum.KeyCode.Q or input.UserInputType == Enum.UserInputType.MouseButton2)
		and ghost then
		setSelected(nil)
	elseif processed then
		return
	elseif input.UserInputType == Enum.UserInputType.MouseButton1 then
		tryBuildAt(UserInputService:GetMouseLocation())
	elseif input.UserInputType == Enum.UserInputType.Touch then
		touchStart[input] = { pos = Vector2.new(input.Position.X, input.Position.Y), t = os.clock() }
	end
end)
UserInputService.InputEnded:Connect(function(input, processed)
	if input.UserInputType ~= Enum.UserInputType.Touch then
		return
	end
	local start = touchStart[input]
	touchStart[input] = nil
	if not start or processed then
		return
	end
	local pos = Vector2.new(input.Position.X, input.Position.Y)
	if (pos - start.pos).Magnitude < 14 and os.clock() - start.t < 0.4 then
		tryBuildAt(pos)
	end
end)

-- ------------------------------------------------------------------ HUD buttons
local top = hud:WaitForChild("TopBar")
onClick(top:FindFirstChild("CarsTab"), function()
	closeWindows()
	request("Teleport", "Cars")
end)
onClick(top:FindFirstChild("StylesTab"), function()
	closeWindows()
	request("Teleport", "Styles")
end)
onClick(top:FindFirstChild("BaseTab"), function()
	closeWindows()
	request("Teleport", "Base")
end)

local left = hud:WaitForChild("LeftMenu")
onClick(left:FindFirstChild("ShopButton"), function()
	open("ShopWindow")
end)
onClick(left:FindFirstChild("IndexButton"), function()
	open("IndexWindow")
end)
onClick(left:FindFirstChild("DailyButton"), function()
	open("DailyWindow")
end)
onClick(left:FindFirstChild("PassButton"), function()
	open("PassWindow")
end)
onClick(rollArea:FindFirstChild("SkillsButton"), function()
	open("SkillsWindow")
end)

local right = hud:WaitForChild("RightMenu")
onClick(right:FindFirstChild("StarterPackButton"), function()
	open("ShopWindow")
end)
onClick(right:FindFirstChild("X2MoneyButton"), function()
	result(request("Purchase", "X2Money"))
end)
onClick(right:FindFirstChild("X2LuckButton"), function()
	result(request("Purchase", "X2Luck"))
end)

local shopBody = windows.ShopWindow.Body
onClick(shopBody.CrateCard:FindFirstChild("Buy1Button"), function()
	result(request("Purchase", "Crate1"))
end)
onClick(shopBody.CrateCard:FindFirstChild("Buy3Button"), function()
	result(request("Purchase", "Crate3"))
end)
onClick(shopBody.StarterCard:FindFirstChild("BuyButton"), function()
	result(request("Purchase", "StarterPack"))
end)

onClick(windows.DailyWindow.Header:FindFirstChild("ClaimAllButton"), function()
	result(request("ClaimDaily"))
end)
for d = 1, 7 do
	local card = windows.DailyWindow.Body:FindFirstChild("Day" .. d)
	onClick(card and card:FindFirstChild("Status"), function()
		result(request("ClaimDaily"))
	end)
end

onClick(windows.PassWindow.Header:FindFirstChild("PremiumButton"), function()
	result(request("Purchase", "PremiumPass"))
end)
onClick(windows.PassWindow.Body.Bottom:FindFirstChild("ClaimButton"), function()
	result(request("ClaimPass"))
end)
onClick(windows.PassWindow.Body.Bottom:FindFirstChild("SkipButton"), function()
	result(request("Purchase", "PassSkip"))
end)

local indexTab = "All"
local indexGrid = windows.IndexWindow.Body.Grid
local IndexPreview = require(ReplicatedStorage:WaitForChild("IndexPreview"))
local function applyIndexFilter()
	for _, p in GameData.Pieces do
		local card = indexGrid:FindFirstChild("Piece_" .. p.id)
		if card then
			card.Visible = indexTab == "All" or p.tier == indexTab
		end
	end
end
for _, tab in windows.IndexWindow.Tabs:GetChildren() do
	if tab:IsA("GuiButton") then
		onClick(tab, function()
			indexTab = string.sub(tab.Name, 5)
			applyIndexFilter()
		end)
	end
end

local selectedSkill = "Root"
local tree = windows.SkillsWindow.Body.Tree
local info = windows.SkillsWindow.Body.Info
local refreshAll -- forward
for _, u in GameData.Upgrades do
	onClick(tree:FindFirstChild("Node_" .. u.id), function()
		selectedSkill = u.id
		info.Visible = true
		refreshAll()
	end)
end
onClick(info:FindFirstChild("BuyButton"), function()
	result(request("BuyUpgrade", selectedSkill))
end)

local carGrid = windows.CarShopWindow.Body.Grid
for _, c in GameData.Cars do
	local card = carGrid:FindFirstChild("Car_" .. c.id)
	if card then
		local model = Assets.Cars:FindFirstChild(c.id)
		if model then
			showInViewport(card:FindFirstChild("Viewport") :: ViewportFrame, model, 7)
		end
		onClick(card:FindFirstChild("PriceButton"), function()
			result(request("BuyCar", c.id))
		end)
	end
end
for _, s in GameData.Styles do
	local card = windows.StyleShopWindow.Body:FindFirstChild("Style_" .. s.id)
	onClick(card and card:FindFirstChild("PriceButton"), function()
		result(request("BuyStyle", s.id))
	end)
end
for _, p in GameData.Potions do
	local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id, true)
	onClick(card and card:FindFirstChild("BuyButton"), function()
		result(request("BuyPotion", p.id))
	end)
end
local FUSE_NEED = GameData.Config.FuseCount or 3
for i, d in GameData.Dice do
	local card = windows.DiceShopWindow.Body:FindFirstChild("Dice_" .. d.id, true)
	onClick(card and card:FindFirstChild("BuyButton"), function()
		result(request("BuyDice", d.id))
	end)
	-- small FUSE button on the card once you own enough of this die
	local buy = card and card:FindFirstChild("BuyButton")
	if buy and i < #GameData.Dice then
		local fuse = systems.freshClone(buy)
		fuse.Name = "FuseButton"
		fuse.AnchorPoint = Vector2.new(1, 0)
		fuse.Position = UDim2.new(1, -8, 0, 36)
		fuse.Size = UDim2.fromOffset(84, 40)
		fuse.ZIndex = buy.ZIndex + 2
		fuse.Visible = false
		fuse.Parent = card
		setPreset(fuse, "purple")
		setText(fuse, "FUSE")
		vfx:BindButton(fuse)
		onClick(fuse, function()
			systems:Open(d.id)
		end)
	end
end
-- a fusion chip at the end of the dice bar above the Roll button
local fuseChip = nil
do
	local first = rollArea.DiceBar:FindFirstChild("Dice_" .. GameData.Dice[1].id)
	if first then
		fuseChip = systems.freshClone(first)
		fuseChip.Name = "FuseChip"
		fuseChip.LayoutOrder = 999
		fuseChip.Visible = false
		for _, c in fuseChip:GetChildren() do
			if c:IsA("ImageLabel") then
				c:Destroy()
			end
		end
		fuseChip.Count.Text = "🔮"
		fuseChip.Count.TextScaled = true
		fuseChip.BackgroundColor3 = Color3.fromHex("#7a3be0")
		fuseChip.BackgroundTransparency = 0
		local tag = fuseChip.Count:Clone()
		tag.Name = "Tag"
		tag.Text = "FUSE"
		tag.Size = UDim2.new(1, 0, 0, 22)
		tag.Position = UDim2.new(0, 0, 1, -20)
		tag.Parent = fuseChip
		fuseChip.Parent = rollArea.DiceBar
		vfx:BindButton(fuseChip)
		onClick(fuseChip, function()
			systems:Open(nil)
		end)
	end
end
local function refreshFuse()
	local data = snap.Data
	local any = false
	for i, d in GameData.Dice do
		local n = data.Dice[d.id] or 0
		local can = n >= FUSE_NEED and i < #GameData.Dice
		any = any or can
		local card = windows.DiceShopWindow.Body:FindFirstChild("Dice_" .. d.id, true)
		local fuse = card and card:FindFirstChild("FuseButton")
		if fuse then
			fuse.Visible = can
		end
	end
	if fuseChip then
		fuseChip.Visible = any
	end
end

local SHOP_WINDOWS = {
	Cars = "CarShopWindow",
	Styles = "StyleShopWindow",
	Potions = "PotionShopWindow",
	Dice = "DiceShopWindow",
}
ProximityPromptService.PromptTriggered:Connect(function(prompt)
	local holder = prompt.Parent
	local shop = holder and holder:GetAttribute("Shop")
	if shop and SHOP_WINDOWS[shop] then
		open(SHOP_WINDOWS[shop])
	end
end)

-- ------------------------------------------------------------------ test commands
-- /alltracks [n]  /cash [n]  /dice [n]  /potions  /mutations [n]  /floor  /offline [hours]
-- Created on the client so they work with any chat setup; the server checks who may use them.
do
	local TextChatService = game:GetService("TextChatService")
	for _, name in { "alltracks", "cash", "dice", "potions", "mutations", "floor", "offline" } do
		local cmd = Instance.new("TextChatCommand")
		cmd.Name = "TrackRNGClient_" .. name
		cmd.PrimaryAlias = "/" .. name
		cmd.Parent = TextChatService
		cmd.Triggered:Connect(function(_source, text)
			local ok, msg = request("DevCommand", text)
			if not ok and msg then
				toast(msg, "#ff8a96")
			end
		end)
	end
end

-- ------------------------------------------------------------------ island style previews
local StylePreview = require(ReplicatedStorage:WaitForChild("StylePreview"))
windows.StyleShopWindow:GetPropertyChangedSignal("Visible"):Connect(function()
	if not windows.StyleShopWindow.Visible then
		return
	end
	for i, s in GameData.Styles do
		local card = windows.StyleShopWindow.Body:FindFirstChild("Style_" .. s.id)
		local vp = card and card:FindFirstChild("Preview")
		if vp then
			vp:SetAttribute("Phase", i * 0.8)
			StylePreview.Render(vp, s.id)
		end
	end
end)

-- ------------------------------------------------------------------ settings (saved on the server)
local settingsBar = hud:FindFirstChild("SettingsBar")
local settings = { Music = true, Sfx = true, Vfx = "High" }
local function applySettings()
	vfx:SetMusic(settings.Music)
	vfx:SetSfx(settings.Sfx)
	vfx:SetQuality(settings.Vfx)
	Mutations.SetQuality(settings.Vfx)
	if settingsBar then
		local art = GameData.UIArt or {}
		settingsBar.MusicToggle.Art.Image = art[if settings.Music then "music_on" else "music_off"] or ""
		settingsBar.SfxToggle.Art.Image = art[if settings.Sfx then "sfx_on" else "sfx_off"] or ""
		settingsBar.VfxToggle.Art.Image = art[if settings.Vfx == "Low" then "vfx_off" else "vfx_on"] or ""
	end
end
local function changeSetting(key: string, value: any)
	settings[key] = value
	applySettings()
	task.spawn(request, "SetSettings", settings)
end
if settingsBar then
	onClick(settingsBar.MusicToggle, function()
		changeSetting("Music", not settings.Music)
	end)
	onClick(settingsBar.SfxToggle, function()
		changeSetting("Sfx", not settings.Sfx)
	end)
	onClick(settingsBar.VfxToggle, function()
		changeSetting("Vfx", if settings.Vfx == "High" then "Low" else "High")
		toast(if settings.Vfx == "High" then "Effects: HIGH" else "Effects: LOW (faster on phones)", "#cfe8ff")
	end)
end
local settingsLoaded = false

-- ------------------------------------------------------------------ rare roll feed
local feed = hud:WaitForChild("RareFeed")
local feedRows = {}
local lastFireworks = 0
Remotes.RareRoll.OnClientEvent:Connect(function(name: string, pieceId: string, mut: string?)
	local piece = Stats.Pieces[pieceId]
	if not piece then
		return
	end
	local m = mut and Stats.Mutations[mut]
	-- fireworks over the hub for everybody's big pulls
	local tc = Color3.fromHex(Stats.Tiers[piece.tier].color)
	if os.clock() - lastFireworks > 2.5 then
		lastFireworks = os.clock()
		worldFX:Fireworks(Vector3.new(0, 104, 0), { tc, Color3.new(1, 1, 1), Color3.fromRGB(255, 214, 64) },
			vfx:Q(if piece.tier == "Secret" then 14 elseif piece.tier == "Mythical" then 10 else 6))
	end
	task.defer(function()
		if uiFX.FeedIn then
			uiFX.FeedIn()
		end
	end)
	table.insert(feedRows, 1, { name = name, piece = piece, mut = m })
	while #feedRows > 5 do
		table.remove(feedRows)
	end
	for i = 1, 5 do
		local row = feed:FindFirstChild("Row" .. i)
		local e = feedRows[i]
		row.Player.Text = if e then e.name else ""
		row.Piece.Text = if e then (if e.mut then e.mut.name .. " " else "") .. e.piece.name else ""
		row.Piece.TextColor3 = if e and e.mut then Mutations.color(e.mut.id)
			elseif e then tierColor(e.piece.tier) else Color3.new(1, 1, 1)
		row.Odds.Text = if e then "1 in " .. Format.short(e.piece.odds * (if e.mut then e.mut.chance else 1)) else ""
	end
	if name ~= player.DisplayName then
		toast(name .. " rolled " .. (if m then m.name .. " " else "") .. piece.name .. "!",
			if m and m.color ~= "rainbow" then m.color else Stats.Tiers[piece.tier].color)
	end
end)

-- ------------------------------------------------------------------ refresh
local function potionLeft(effect: string): number
	if not snap then
		return 0
	end
	local left = snap.Data.Potions[effect] or 0
	return math.max(0, left - (os.clock() - snapTime))
end

-- celebrate lifetime earnings milestones (1K, 10K, 100K, ...), but not the ones already
-- passed when the player joins
local milestone = nil
local function checkMilestone(total: number)
	local step = if total >= 1000 then 10 ^ math.floor(math.log10(total)) else 0
	if milestone == nil then
		milestone = step
	elseif step > milestone then
		milestone = step
		vfx:Milestone(Format.money(step) .. " EARNED!")
	end
end

-- the cash label counts up to the new value and gives a little bump when it grows
local shownCash = nil
local cashValue = Instance.new("NumberValue")
cashValue.Changed:Connect(function(v)
	hud.CashPanel.Amount.Text = Format.money(math.floor(v + 0.5))
end)
local cashBump = Instance.new("UIScale")
cashBump.Name = "CountBump"
cashBump.Parent = hud.CashPanel.Amount
local function countCash(cash: number)
	if shownCash == nil or cash < shownCash or cash - shownCash > shownCash * 50 then
		cashValue.Value = cash
	elseif cash > shownCash then
		TweenService:Create(cashValue, TweenInfo.new(0.45, Enum.EasingStyle.Quad), { Value = cash }):Play()
		cashBump.Scale = 1.08
		TweenService:Create(cashBump, TweenInfo.new(0.3, Enum.EasingStyle.Back), { Scale = 1 }):Play()
	end
	shownCash = cash
	hud.CashPanel.Amount.Text = Format.money(math.floor(cashValue.Value + 0.5))
end

local function refreshHUD()
	local data = snap.Data
	local cash = player:GetAttribute("Cash") or data.Cash
	countCash(cash)
	checkMilestone(data.TotalEarned or 0)
	windows.SkillsWindow.Header.Cash.Amount.Text = Format.money(cash)
	hud.IncomeLabel.Text = "+" .. Format.money(snap.Income) .. "/s"
	local st = hud.Stats
	st.Luck.Text = string.format("%.2fx", snap.Luck)
	st.RollTime.Text = string.format("%.2fs", snap.RollTime)
	st.FriendBoost.Text = "👥 +" .. math.floor(Stats.friendBoost(snap.Friends) * 100) .. "%"
	local er = hud.Earnings
	er.ElementsText.Text = "🧱 Elements " .. #data.Placed .. "/" .. snap.MaxElements
	er.OfflineAmount.Text = Format.money((snap.BaseIncome or snap.Income) * 3600 * GameData.Config.OfflineRate)
	local auto = rollArea.AutoButton
	setPreset(auto, if data.AutoRoll then "green" else "gray")
	auto.Sub.Text = if data.AutoRoll then "ON" else "OFF"
	rollReveal:SetAuto(data.AutoRoll)
	uiFX:SetAuto(data.AutoRoll == true)
	for _, d in GameData.Dice do
		local chip = rollArea.DiceBar:FindFirstChild("Dice_" .. d.id)
		if chip then
			local n = data.Dice[d.id] or 0
			chip.Count.Text = tostring(n)
			chip.Visible = n > 0
			chip.BackgroundTransparency = if chip:FindFirstChild("AtlasImage") then 1 else (if n > 0 then 0 else 0.55)
			local atlasImage = chip:FindFirstChild("AtlasImage")
			if atlasImage then atlasImage.ImageTransparency = if n > 0 then 0 else 0.5 end
		end
	end
	right.X2MoneyButton.Sub.Text = if data.Passes.X2Money then "OWNED"
		else "\u{E002}" .. GameData.Products.Gamepasses.X2Money.price
	right.X2LuckButton.Sub.Text = if data.Passes.X2Luck then "OWNED"
		else "\u{E002}" .. GameData.Products.Gamepasses.X2Luck.price
	right.StarterPackButton.Visible = not data.StarterPack
	-- affordable skills badge
	local affordable = 0
	for _, u in GameData.Upgrades do
		if not data.Upgrades[u.id] and (not u.requires or data.Upgrades[u.requires])
			and cash >= u.cost then
			affordable += 1
		end
	end
	local badge = rollArea.SkillsButton.Badge
	badge.Visible = affordable > 0
	badge.Text.Text = tostring(affordable)
end

local function refreshBuild()
	local data = snap.Data
	buildPanel.Counter.Text = "Elements " .. #data.Placed .. "/" .. snap.MaxElements
	for _, pc in GameData.Pieces do
		local item = buildPanel.Items:FindFirstChild("Item_" .. pc.id)
		if item then
			local n = data.Inventory[pc.id] or 0
			item.Count.Text = "x" .. n
			item.Visible = n > 0 or data.Discovered[pc.id] == true
			item.BackgroundTransparency = if n > 0 then 0 else 0.5
		end
	end
	-- mutated copies get their own cards; empty ones disappear
	for key, n in data.Inventory do
		if n > 0 and string.find(key, "@", 1, true) then
			local card = variantCard(key)
			if card then
				(card :: any).Count.Text = "x" .. n
			end
		end
	end
	for _, item in buildPanel.Items:GetChildren() do
		if item:IsA("GuiButton") and string.find(item.Name, "@", 1, true) then
			local key = string.sub(item.Name, 6)
			if (data.Inventory[key] or 0) <= 0 then
				item:Destroy()
			end
		end
	end
	if selected and (data.Inventory[selected] or 0) <= 0 then
		setSelected(nil)
	end
end

local function dailyInfo()
	local data = snap.Data
	local now = snap.ServerTime + (os.clock() - snapTime)
	local cfg = GameData.Config
	local streak = data.Daily.Streak
	if data.Daily.Last > 0 and now - data.Daily.Last > cfg.DailyResetHours * 3600 then
		streak = 0
	end
	if streak >= 7 then
		streak = 0
	end
	local wait = 0
	if data.Daily.Last > 0 then
		wait = data.Daily.Last + cfg.DailyCooldownHours * 3600 - now
	end
	return streak, wait <= 0, wait
end

local function refreshDaily()
	local streak, ready, wait = dailyInfo()
	local body = windows.DailyWindow.Body
	for d = 1, 7 do
		local card = body:FindFirstChild("Day" .. d)
		local status = card and card:FindFirstChild("Status")
		if status then
			if d <= streak then
				setPreset(status, "gray")
				setText(status, "CLAIMED")
			elseif d == streak + 1 and ready then
				setPreset(status, "green")
				setText(status, "CLAIM")
			else
				setPreset(status, "gray")
				setText(status, "LOCKED")
			end
		end
	end
	body.Timer.Text = if ready then "Your reward is ready!" else "Next reward in " .. Format.time(wait)
	left.DailyButton.Badge.Visible = ready
end

local function refreshIndex()
	local data = snap.Data
	local found = 0
	for _, p in GameData.Pieces do
		local card = indexGrid:FindFirstChild("Piece_" .. p.id)
		if card then
			local known = data.Discovered[p.id] == true
			if known then
				found += 1
			end
			card.Known.Visible = known
			IndexPreview.Render(card, Tiles:FindFirstChild(p.id), known)
			local placed = 0
			for _, t in data.Placed do
				if t.id == p.id then
					placed += 1
				end
			end
			card.Known.Count.Text = "x" .. (Stats.ownedCount(data, p.id) + placed)
			-- mutation collection: one dot per mutation, lit once you have rolled it
			local dots = card.Known:FindFirstChild("Mutations")
			if not dots then
				dots = Instance.new("Frame")
				dots.Name = "Mutations"
				dots.BackgroundTransparency = 1
				dots.AnchorPoint = Vector2.new(0.5, 0)
				dots.Position = UDim2.new(0.5, 0, 1, -62)
				dots.Size = UDim2.fromOffset(6 * 22, 16)
				local layout = Instance.new("UIListLayout")
				layout.FillDirection = Enum.FillDirection.Horizontal
				layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
				layout.Padding = UDim.new(0, 6)
				layout.SortOrder = Enum.SortOrder.LayoutOrder
				layout.Parent = dots
				for _, m in Stats.MutationList do
					local dot = Instance.new("Frame")
					dot.Name = m.id
					dot.LayoutOrder = m.order
					dot.Size = UDim2.fromOffset(14, 14)
					local cr = Instance.new("UICorner")
					cr.CornerRadius = UDim.new(1, 0)
					cr.Parent = dot
					local st = Instance.new("UIStroke")
					st.Thickness = 2
					st.Color = Color3.fromHex("#15131f")
					st.Parent = dot
					local g = Instance.new("UIGradient")
					g.Color = Mutations.sequence(m.id)
					g.Rotation = 45
					g.Parent = dot
					dot.Parent = dots
				end
				dots.Parent = card.Known
			end
			local seen = data.MutDiscovered or {}
			for _, m in Stats.MutationList do
				local dot = dots:FindFirstChild(m.id) :: Frame?
				if dot then
					local got = seen[Stats.invKey(p.id, m.id)] == true
					dot.BackgroundColor3 = if got then Color3.new(1, 1, 1) else Color3.fromHex("#3a3f52")
					dot.BackgroundTransparency = if got then 0 else 0.35
					local g = dot:FindFirstChildOfClass("UIGradient")
					if g then
						g.Enabled = got
					end
				end
			end
		end
	end
	windows.IndexWindow.Counter.Text = found .. "/" .. #GameData.Pieces .. " Found"
	applyIndexFilter()
end

local function refreshPass()
	local data = snap.Data
	local trackFrame = windows.PassWindow.Body.Track
	for _, entry in GameData.Pass do
		local col = trackFrame:FindFirstChild("Level_" .. entry.level)
		if col then
			local k = tostring(entry.level)
			local unlocked = entry.level <= data.Level
			for _, kind in { "Free", "Premium" } do
				local cell = col:FindFirstChild(kind)
				local claimed = if kind == "Free" then data.PassClaimed.free[k]
					else data.PassClaimed.premium[k]
				local allowed = kind == "Free" or data.Passes.PremiumPass == true
				cell.Check.Visible = claimed == true
				cell.Lock.Visible = not claimed and (not unlocked or not allowed)
				cell.Claimable.Visible = not claimed and unlocked and allowed
			end
		end
	end
	local bottom = windows.PassWindow.Body.Bottom
	bottom.LevelText.Text = "Lvl " .. data.Level
	local need = Stats.xpForLevel(data.Level)
	bottom.Bar.Fill.Size = UDim2.fromScale(math.clamp(data.XP / need, 0, 1), 1)
	bottom.Bar.Text.Text = data.XP .. "/" .. need .. " XP"
	setText(windows.PassWindow.Header.PremiumButton,
		if data.Passes.PremiumPass then "Premium ✔" else "Premium Pass")
end

local function refreshSkills()
	local data = snap.Data
	for _, u in GameData.Upgrades do
		local node = tree:FindFirstChild("Node_" .. u.id)
		if node then
			local owned = data.Upgrades[u.id] == true
			local available = not u.requires or data.Upgrades[u.requires] == true
			node.Owned.Visible = owned
			node.Locked.Visible = not owned and not available
			node.Level.Text = if owned then "" else Format.money(u.cost)
			local stroke = node:FindFirstChild("Stroke") :: UIStroke
			if stroke then
				stroke.Color = if u.id == selectedSkill then Color3.fromHex("#ffffff")
					elseif owned then Color3.fromHex("#ffd23b")
					else Color3.fromHex("#15131f")
			end
		end
		local line = tree:FindFirstChild("Line_" .. u.id)
		if line then
			line.BackgroundColor3 = if data.Upgrades[u.id] then Color3.fromHex("#ffd23b")
				else Color3.fromHex("#4a5578")
		end
	end
	local u = Stats.Upgrades[selectedSkill]
	info.Icon.Text = u.icon
	UIIconAtlas.SetIcon(info.Icon, u.icon, gui:GetAttribute("IconAtlas"))
	info.NameText.Text = u.name
	info.DescText.Text = u.desc
	info.CostText.Text = Format.money(u.cost)
	local buy = info.BuyButton
	if data.Upgrades[u.id] then
		setPreset(buy, "gray")
		setText(buy, "OWNED")
	elseif u.requires and not data.Upgrades[u.requires] then
		setPreset(buy, "red")
		setText(buy, "LOCKED")
	else
		setPreset(buy, "green")
		setText(buy, "BUY")
	end
	UIVisuals.RefreshSkills(tree, selectedSkill, data.Upgrades, player:GetAttribute("Cash") or data.Cash)
end

local function refreshShops()
	local data = snap.Data
	for _, c in GameData.Cars do
		local card = carGrid:FindFirstChild("Car_" .. c.id)
		if card then
			local b = card.PriceButton
			if data.EquippedCar == c.id then
				setPreset(b, "gray")
				setText(b, "EQUIPPED")
			elseif data.Cars[c.id] then
				setPreset(b, "blue")
				setText(b, "EQUIP")
			else
				setPreset(b, "green")
				setText(b, if c.price == 0 then "FREE" else Format.money(c.price))
			end
		end
	end
	for _, s in GameData.Styles do
		local card = windows.StyleShopWindow.Body:FindFirstChild("Style_" .. s.id)
		if card then
			local b = card.PriceButton
			if data.EquippedStyle == s.id then
				setPreset(b, "gray")
				setText(b, "EQUIPPED")
			elseif data.Styles[s.id] then
				setPreset(b, "blue")
				setText(b, "EQUIP")
			else
				setPreset(b, "green")
				setText(b, if s.price == 0 then "FREE" else Format.money(s.price))
			end
		end
	end
	for _, d in GameData.Dice do
		local card = windows.DiceShopWindow.Body:FindFirstChild("Dice_" .. d.id, true)
		if card then
			card.OwnedText.Text = "Owned: " .. (data.Dice[d.id] or 0)
		end
	end
	local starter = windows.ShopWindow.Body.StarterCard
	starter.BuyButton.Visible = not data.StarterPack
	starter.Owned.Visible = data.StarterPack == true
end

local function refreshTimers()
	if not snap then
		return
	end
	local holder = hud.ActivePotions
	for _, p in GameData.Potions do
		local secs = potionLeft(p.effect)
		local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id, true)
		if card then
			card.TimerText.Text = if secs > 0 then "Active: " .. Format.time(secs) else ""
		end
		local t = holder:FindFirstChild(p.effect)
		if secs > 0 then
			if not t then
				t = templates.PotionTimer:Clone()
				t.Name = p.effect
				t.Icon.Text = p.icon
				local art = t.Icon:FindFirstChild("AtlasImage")
				if art and p.image then
					art.Image = p.image
					art.ImageRectOffset = Vector2.zero
					art.ImageRectSize = Vector2.zero
					art.Size = UDim2.fromScale(1.15, 1.15)
				end
				t.Visible = true
				t.Parent = holder
			end
			t.Time.Text = Format.time(secs)
		elseif t then
			t:Destroy()
		end
	end
	refreshDaily()
end

function refreshAll()
	if not snap then
		return
	end
	refreshHUD()
	refreshBuild()
	refreshDaily()
	refreshIndex()
	refreshPass()
	refreshSkills()
	refreshShops()
	refreshFuse()
end

Remotes.DataUpdate.OnClientEvent:Connect(function(s)
	snap = s
	snapTime = os.clock()
	placedCache = Stats.placedMap(s.Data)
	systems:SetSnap(s)
	if buildPanel.Visible then
		worldFX:ShowRoute(myPlot(), s.Data, true)
	end
	if not settingsLoaded and s.Data.Settings then
		settingsLoaded = true
		for k, v in s.Data.Settings do
			settings[k] = v
		end
		applySettings()
	end
	refreshAll()
end)

player:GetAttributeChangedSignal("Cash"):Connect(function()
	if snap then
		refreshHUD()
	end
end)

Remotes.Notify.OnClientEvent:Connect(function(text, color)
	toast(text, color)
end)

-- floating "+$" text where the car finished a tile; fast cars finish many tiles a second, so
-- popups are merged (at most ~7 per second, the amounts add up)
local earnPending = 0
local lastEarnPopup = 0
Remotes.Earned.OnClientEvent:Connect(function(amount: number, pos: Vector3)
	earnPending += amount
	if os.clock() - lastEarnPopup < 0.14 then
		return
	end
	lastEarnPopup = os.clock()
	amount = earnPending
	earnPending = 0
	vfx:Earn(amount, pos)
	uiFX:CashGleam()
	local cam = Workspace.CurrentCamera
	if not cam or (cam.CFrame.Position - pos).Magnitude > 250 then
		return
	end
	local anchor = Instance.new("Part")
	anchor.Anchored = true
	anchor.CanCollide = false
	anchor.CanQuery = false
	anchor.CanTouch = false
	anchor.Transparency = 1
	anchor.Size = Vector3.one
	anchor.CFrame = CFrame.new(pos + Vector3.new(0, 3, 0))
	local bb = Instance.new("BillboardGui")
	bb.Size = UDim2.fromOffset(160, 44)
	bb.AlwaysOnTop = true
	bb.Parent = anchor
	local lbl = Instance.new("TextLabel")
	lbl.BackgroundTransparency = 1
	lbl.Size = UDim2.fromScale(1, 1)
	lbl.Text = "+" .. Format.money(amount)
	lbl.TextScaled = true
	lbl.FontFace = Font.new("rbxasset://fonts/families/FredokaOne.json", Enum.FontWeight.Bold)
	lbl.TextColor3 = Color3.fromHex("#7dff4f")
	local st = Instance.new("UIStroke")
	st.Thickness = 3
	st.Color = Color3.fromHex("#15131f")
	st.Parent = lbl
	lbl.Parent = bb
	anchor.Parent = Workspace
	TweenService:Create(anchor, TweenInfo.new(1), { CFrame = anchor.CFrame + Vector3.new(0, 5, 0) }):Play()
	TweenService:Create(lbl, TweenInfo.new(1), { TextTransparency = 1 }):Play()
	TweenService:Create(st, TweenInfo.new(1), { Transparency = 1 }):Play()
	task.delay(1.05, function()
		anchor:Destroy()
	end)
end)

-- cooldown overlay, timers and auto roll
local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if snap then
		local frac = math.clamp((os.clock() - lastRollClock) / snap.RollTime, 0, 1)
		rollButton.Die.Cooldown.Size = UDim2.fromScale(1, 1 - frac)
		if snap.Data.AutoRoll and frac >= 1 and not busy then
			task.spawn(doRoll, true)
		end
	end
	if acc >= 1 then
		acc = 0
		refreshTimers()
	end
end)

task.spawn(function()
	for _ = 1, 20 do
		local ok, _, s = request("GetData")
		if ok and s then
			snap = s
			snapTime = os.clock()
			placedCache = Stats.placedMap(s.Data)
			systems:SetSnap(s)
			refreshAll()
			return
		end
		task.wait(1)
	end
end)

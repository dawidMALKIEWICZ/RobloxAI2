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
local hud = root:WaitForChild("HUD")
local windows = root:WaitForChild("Windows")
local buildPanel = root:WaitForChild("BuildPanel")
local reel = root:WaitForChild("RollReel")
local toasts = root:WaitForChild("Toasts")
local templates = root:WaitForChild("Templates")

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
	local ok, a, b, c = pcall(function()
		return Remotes.Request:InvokeServer(action, arg)
	end)
	if not ok then
		return false, "Connection error"
	end
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
	local s = Instance.new("UIScale")
	s.Name = "Bounce"
	s.Parent = button
	button.MouseEnter:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.12), { Scale = 1.06 }):Play()
	end)
	button.MouseLeave:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.12), { Scale = 1 }):Play()
	end)
	button.MouseButton1Down:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.06), { Scale = 0.9 }):Play()
	end)
	button.MouseButton1Up:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.1), { Scale = 1.06 }):Play()
	end)
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
	local s = w:FindFirstChild("Pop") :: UIScale
	if not s then
		s = Instance.new("UIScale")
		s.Name = "Pop"
		s.Parent = w
	end
	s.Scale = 0.85
	TweenService:Create(s, TweenInfo.new(0.18, Enum.EasingStyle.Back), { Scale = 1 }):Play()
end

for _, w in windows:GetChildren() do
	local header = w:FindFirstChild("Header")
	onClick(header and header:FindFirstChild("Close"), closeWindows)
end

-- ------------------------------------------------------------------ roll reel
local CARD_W = 196
local REEL_CARDS = 26
local RESULT_INDEX = 22
local strip = reel:WaitForChild("Clip"):WaitForChild("Strip")
local cards = {}
for i = 1, REEL_CARDS do
	local c = templates:WaitForChild("ReelCard"):Clone()
	c.Position = UDim2.fromOffset((i - 1) * CARD_W, 10)
	c.Visible = true
	c.Parent = strip
	cards[i] = c
end

local function randomReelPiece()
	-- mostly commons, sometimes something shiny so the reel looks exciting
	local r = math.random()
	local list = Stats.PieceList
	if r < 0.55 then
		return list[math.random(1, 3)]
	elseif r < 0.85 then
		return list[math.random(4, 9)]
	end
	return list[math.random(10, #list)]
end

local function fillCard(card: Frame, piece)
	(card:FindFirstChild("Name") :: TextLabel).Text = piece.name
	local odds = card:FindFirstChild("Odds") :: TextLabel
	odds.Text = "1 in " .. Format.short(piece.odds)
	odds.TextColor3 = tierColor(piece.tier)
	local stroke = card:FindFirstChild("Stroke") :: UIStroke
	if stroke then
		stroke.Color = tierColor(piece.tier)
	end
	local tile = Tiles:FindFirstChild(piece.id)
	if tile then
		showInViewport(card:FindFirstChild("Viewport") :: ViewportFrame, tile, 15)
	end
end

local reelToken = 0
local function playReel(res, fast: boolean)
	local piece = Stats.Pieces[res.piece]
	if not piece then
		return
	end
	reelToken += 1
	local token = reelToken
	for i, card in cards do
		fillCard(card, if i == RESULT_INDEX then piece else randomReelPiece())
	end
	local resultLbl = reel:FindFirstChild("Result") :: TextLabel
	resultLbl.Text = ""
	local highlight = reel:FindFirstChild("Highlight") :: Frame
	highlight.BackgroundTransparency = 1
	reel.Visible = true
	local function centerOn(i: number, jitter: number)
		return UDim2.new(0.5, -((i - 1) * CARD_W + CARD_W / 2) + jitter, 0, 0)
	end
	strip.Position = centerOn(2, 0)
	local dur = if fast then 0.7 else 2.4
	local tw = TweenService:Create(strip, TweenInfo.new(dur, Enum.EasingStyle.Quint,
		Enum.EasingDirection.Out), { Position = centerOn(RESULT_INDEX, math.random(-40, 40)) })
	tw:Play()
	tw.Completed:Wait()
	if token ~= reelToken then
		return
	end
	TweenService:Create(strip, TweenInfo.new(0.25), { Position = centerOn(RESULT_INDEX, 0) }):Play()
	highlight.BackgroundTransparency = 0.8
	resultLbl.Text = (if res.new then "NEW! " else "") .. piece.name .. " added to your Build menu!"
	resultLbl.TextColor3 = tierColor(piece.tier)
	task.delay(if fast then 1.0 else 2.0, function()
		if token == reelToken then
			reel.Visible = false
		end
	end)
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
	busy = true
	lastRollClock = os.clock()
	local ok, msg, res = request("Roll")
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
onClick(rollArea:FindFirstChild("AutoButton"), function()
	if snap then
		result(request("SetAuto", not snap.Data.AutoRoll))
	end
end)
for _, d in GameData.Dice do
	onClick(rollArea.DiceBar:FindFirstChild("Dice_" .. d.id), function()
		local ok, msg, res = request("UseDice", d.id)
		if ok and res then
			task.spawn(playReel, res, false)
		else
			result(ok, msg)
		end
	end)
end
Remotes.Rolled.OnClientEvent:Connect(function(res)
	playReel(res, false)
end)

-- ------------------------------------------------------------------ build mode
local selected: string? = nil
local rotation = 0
local deleteMode = false
local ghost: Model? = nil
local ghostHighlight: Highlight? = nil

local function myPlot(): Model?
	for _, plot in Workspace:WaitForChild("Map"):WaitForChild("Plots"):GetChildren() do
		if plot:GetAttribute("OwnerId") == player.UserId then
			return plot
		end
	end
	return nil
end

local function cellCFrame(plot: Model, x: number, z: number, r: number): CFrame
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local c = Stats.center()
	local cell = Stats.Config.Cell
	return origin * CFrame.new((x - c) * cell, 0.3, (z - c) * cell) * CFrame.Angles(0, -r * math.pi / 2, 0)
end

local function clearGhost()
	if ghost then
		ghost:Destroy()
		ghost = nil
	end
	ghostHighlight = nil
end

local function makeGhost(id: string)
	clearGhost()
	local template = Tiles:FindFirstChild(id)
	if not template then
		return
	end
	local g = template:Clone()
	local path = g:FindFirstChild("Path")
	if path then
		path:Destroy()
	end
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

local function setSelected(id: string?)
	selected = id
	deleteMode = false
	if id then
		makeGhost(id)
	else
		clearGhost()
	end
	for _, item in buildPanel.Items:GetChildren() do
		if item:IsA("GuiButton") then
			local stroke = item:FindFirstChild("Stroke") :: UIStroke
			local pid = string.sub(item.Name, 6)
			stroke.Thickness = if pid == id then 7 else 4
		end
	end
	setPreset(buildPanel.DeleteButton, "red")
	setText(buildPanel.DeleteButton, "Delete")
end

function closeBuild()
	buildPanel.Visible = false
	setSelected(nil)
	deleteMode = false
end

local function openBuild()
	closeWindows()
	reel.Visible = false
	buildPanel.Visible = true
	request("Teleport", "Base")
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
for _, pc in GameData.Pieces do
	local item = buildPanel.Items:FindFirstChild("Item_" .. pc.id)
	if item then
		local tile = Tiles:FindFirstChild(pc.id)
		if tile then
			showInViewport(item:FindFirstChild("Viewport") :: ViewportFrame, tile, 15)
		end
		onClick(item, function()
			if not snap or (snap.Data.Inventory[pc.id] or 0) <= 0 then
				toast("Roll the dice to get more " .. pc.name .. "!", "#ff8a96")
				return
			end
			setSelected(if selected == pc.id then nil else pc.id)
		end)
	end
end

local function pointerCell(plot: Model, screenPos: Vector2)
	local cam = Workspace.CurrentCamera
	local ray = cam:ViewportPointToRay(screenPos.X, screenPos.Y)
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local planeY = origin.Position.Y + 0.3
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
	if not snap then
		return false
	end
	local data = snap.Data
	return Stats.inUnlocked(data, x, z) and not Stats.isStart(x, z)
		and not Stats.placedMap(data)[Stats.cellKey(x, z)]
		and #data.Placed < snap.MaxElements
end

RunService.RenderStepped:Connect(function()
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
		ghost:PivotTo(cellCFrame(plot, cell.x, cell.z, 0) * CFrame.new(0, 1.5, 0))
		return
	end
	ghost:PivotTo(cellCFrame(plot, cell.x, cell.z, rotation))
	if ghostHighlight then
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
	if deleteMode then
		local ok, msg = request("Remove", { x = cell.x, z = cell.z })
		if not ok and msg then
			toast(msg, "#ff8a96")
		end
		return
	end
	if selected then
		local id = selected
		local ok, msg = request("Place", { x = cell.x, z = cell.z, r = rotation, id = id })
		if not ok and msg then
			toast(msg, "#ff8a96")
		elseif ok and snap and (snap.Data.Inventory[id] or 0) <= 0 then
			setSelected(nil)
		end
	end
end

UserInputService.InputBegan:Connect(function(input, processed)
	if input.KeyCode == Enum.KeyCode.R and not processed then
		rotation = (rotation + 1) % 4
	elseif (input.KeyCode == Enum.KeyCode.Q or input.UserInputType == Enum.UserInputType.MouseButton2)
		and ghost then
		setSelected(nil)
	elseif processed then
		return
	elseif input.UserInputType == Enum.UserInputType.MouseButton1 then
		tryBuildAt(UserInputService:GetMouseLocation())
	elseif input.UserInputType == Enum.UserInputType.Touch then
		tryBuildAt(Vector2.new(input.Position.X, input.Position.Y))
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
	local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id)
	onClick(card and card:FindFirstChild("BuyButton"), function()
		result(request("BuyPotion", p.id))
	end)
end
for _, d in GameData.Dice do
	local card = windows.DiceShopWindow.Body:FindFirstChild("Dice_" .. d.id)
	onClick(card and card:FindFirstChild("BuyButton"), function()
		result(request("BuyDice", d.id))
	end)
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

-- ------------------------------------------------------------------ rare roll feed
local feed = hud:WaitForChild("RareFeed")
local feedRows = {}
Remotes.RareRoll.OnClientEvent:Connect(function(name: string, pieceId: string)
	local piece = Stats.Pieces[pieceId]
	if not piece then
		return
	end
	table.insert(feedRows, 1, { name = name, piece = piece })
	while #feedRows > 5 do
		table.remove(feedRows)
	end
	for i = 1, 5 do
		local row = feed:FindFirstChild("Row" .. i)
		local e = feedRows[i]
		row.Player.Text = if e then e.name else ""
		row.Piece.Text = if e then e.piece.name else ""
		row.Piece.TextColor3 = if e then tierColor(e.piece.tier) else Color3.new(1, 1, 1)
		row.Odds.Text = if e then "1 in " .. Format.short(e.piece.odds) else ""
	end
	if name ~= player.DisplayName then
		toast(name .. " rolled " .. piece.name .. "!", Stats.Tiers[piece.tier].color)
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

local function refreshHUD()
	local data = snap.Data
	local cash = player:GetAttribute("Cash") or data.Cash
	hud.CashPanel.Amount.Text = Format.money(cash)
	hud.IncomeLabel.Text = "+" .. Format.money(snap.Income) .. "/s"
	local st = hud.Stats
	st.Luck.Text = string.format("%.2fx", snap.Luck)
	st.RollTime.Text = string.format("%.2fs", snap.RollTime)
	st.FriendBoost.Text = "👥 +" .. math.floor(Stats.friendBoost(snap.Friends) * 100) .. "%"
	local er = hud.Earnings
	er.ElementsText.Text = "🧱 Elements " .. #data.Placed .. "/" .. snap.MaxElements
	er.OfflineAmount.Text = Format.money(snap.Income * 3600 * GameData.Config.OfflineRate)
	local auto = rollArea.AutoButton
	setPreset(auto, if data.AutoRoll then "green" else "gray")
	auto.Sub.Text = if data.AutoRoll then "ON" else "OFF"
	for _, d in GameData.Dice do
		local chip = rollArea.DiceBar:FindFirstChild("Dice_" .. d.id)
		if chip then
			local n = data.Dice[d.id] or 0
			chip.Count.Text = tostring(n)
			chip.BackgroundTransparency = if n > 0 then 0 else 0.55
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
				setPreset(status, "red")
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
			card.Unknown.Visible = not known
			card.Known.Visible = known
			local placed = 0
			for _, t in data.Placed do
				if t.id == p.id then
					placed += 1
				end
			end
			card.Known.Count.Text = "x" .. ((data.Inventory[p.id] or 0) + placed)
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
		local card = windows.DiceShopWindow.Body:FindFirstChild("Dice_" .. d.id)
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
		local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id)
		if card then
			card.TimerText.Text = if secs > 0 then "Active: " .. Format.time(secs) else ""
		end
		local t = holder:FindFirstChild(p.effect)
		if secs > 0 then
			if not t then
				t = templates.PotionTimer:Clone()
				t.Name = p.effect
				t.Icon.Text = p.icon
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
end

Remotes.DataUpdate.OnClientEvent:Connect(function(s)
	snap = s
	snapTime = os.clock()
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

-- floating "+$" text where the car finished a tile
Remotes.Earned.OnClientEvent:Connect(function(amount: number, pos: Vector3)
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
			refreshAll()
			return
		end
		task.wait(1)
	end
end)

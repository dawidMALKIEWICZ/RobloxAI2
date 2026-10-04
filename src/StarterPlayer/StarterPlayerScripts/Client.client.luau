-- Connects the pre-built MainGui (StarterGui) to the server. The UI itself is not created here,
-- this script only fills in values and reacts to clicks.
local Players = game:GetService("Players")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Workspace = game:GetService("Workspace")

local GameData = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameData"))
local Stats = require(ReplicatedStorage.Shared:WaitForChild("Stats"))
local Format = require(ReplicatedStorage.Shared:WaitForChild("Format"))
local Remotes = ReplicatedStorage:WaitForChild("Remotes")
local Assets = ReplicatedStorage:WaitForChild("Assets")

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("MainGui")
local root = gui:WaitForChild("Root")
local hud = root:WaitForChild("HUD")
local windows = root:WaitForChild("Windows")
local spinPopup = root:WaitForChild("SpinPopup")
local toasts = root:WaitForChild("Toasts")
local templates = gui:WaitForChild("Templates")

local snap = nil -- latest snapshot from the server
local snapTime = 0
local busy = false
local lastSpinClock = 0

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
	yellow = seq("#fff59a", "#ffc61a", "#e58a00"),
	purple = seq("#e6b3ff", "#a94dff", "#6a1fc9"),
	blue = seq("#a6e9ff", "#33aaff", "#1563c9"),
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

-- ------------------------------------------------------------------ scaling
local scale = root:WaitForChild("Scale") :: UIScale
local function rescale()
	local cam = Workspace.CurrentCamera
	if not cam then
		return
	end
	local vp = cam.ViewportSize
	local s = math.min(vp.X / 1920, vp.Y / 1080)
	s = math.max(s, 0.3)
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

local function toast(text: string, color: string?)
	local t = templates:WaitForChild("Toast"):Clone()
	local lbl = t:FindFirstChild("Text") :: TextLabel
	lbl.Text = text
	lbl.TextColor3 = Color3.fromHex(color or "#ffffff")
	t.LayoutOrder = math.floor(os.clock() * 100)
	t.Parent = toasts
	task.delay(3, function()
		TweenService:Create(lbl, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
		TweenService:Create(t, TweenInfo.new(0.4), { BackgroundTransparency = 1 }):Play()
		task.wait(0.45)
		t:Destroy()
	end)
	while #toasts:GetChildren() > 5 do
		for _, c in toasts:GetChildren() do
			if c:IsA("Frame") then
				c:Destroy()
				break
			end
		end
	end
end

local function result(ok, msg)
	if msg then
		toast(msg, if ok then "#9dff7a" else "#ff8a96")
	end
end

-- button bounce on press
local function bounce(button: GuiButton)
	local s = button:FindFirstChild("Bounce") :: UIScale
	if not s then
		s = Instance.new("UIScale")
		s.Name = "Bounce"
		s.Parent = button
	end
	button.MouseEnter:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.12), { Scale = 1.05 }):Play()
	end)
	button.MouseLeave:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.12), { Scale = 1 }):Play()
	end)
	button.MouseButton1Down:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.06), { Scale = 0.92 }):Play()
	end)
	button.MouseButton1Up:Connect(function()
		TweenService:Create(s, TweenInfo.new(0.1), { Scale = 1.05 }):Play()
	end)
end
for _, d in root:GetDescendants() do
	if d:IsA("GuiButton") then
		bounce(d)
	end
end

local function onClick(button: Instance?, fn: () -> ())
	if button and button:IsA("GuiButton") then
		button.Activated:Connect(fn)
	end
end

-- ------------------------------------------------------------------ windows
local openWindow: GuiObject? = nil

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

-- ------------------------------------------------------------------ spin
local reelNames = {}
for _, p in GameData.Pieces do
	table.insert(reelNames, p)
end

local popupToken = 0
local function showRoll(res, animate: boolean)
	local piece = Stats.Pieces[res.piece]
	if not piece then
		return
	end
	popupToken += 1
	local token = popupToken
	local tierColor = Color3.fromHex(Stats.Tiers[piece.tier].color)
	local nameLbl = spinPopup:FindFirstChild("PieceName") :: TextLabel
	local icon = spinPopup:FindFirstChild("Icon") :: TextLabel
	local tierLbl = spinPopup:FindFirstChild("Tier") :: TextLabel
	local odds = spinPopup:FindFirstChild("Odds") :: TextLabel
	local status = spinPopup:FindFirstChild("Status") :: TextLabel
	local header = spinPopup:FindFirstChild("Header") :: TextLabel
	spinPopup.Visible = true
	status.Text = ""
	if animate then
		header.Text = "ROLLING..."
		for i = 1, 12 do
			local r = reelNames[math.random(1, #reelNames)]
			nameLbl.Text = r.name
			icon.Text = r.icon
			tierLbl.Text = r.tier
			tierLbl.TextColor3 = Color3.fromHex(Stats.Tiers[r.tier].color)
			odds.Text = "1 in " .. Format.commas(r.odds)
			task.wait(0.03 + i * 0.008)
			if token ~= popupToken then
				return
			end
		end
	end
	header.Text = if res.source == "Spin" then "YOU ROLLED" else string.upper(res.source)
	nameLbl.Text = piece.name
	icon.Text = piece.icon
	tierLbl.Text = piece.tier .. (if res.new then "  NEW!" else "")
	tierLbl.TextColor3 = if piece.tier == "Secret" then Color3.new(1, 1, 1) else tierColor
	odds.Text = "1 in " .. Format.commas(piece.odds)
	if res.placed then
		status.Text = "Added to your track!"
		status.TextColor3 = Color3.fromHex("#9dff7a")
	else
		status.Text = "Not better than your track: +" .. Format.money(res.bonus)
		status.TextColor3 = Color3.fromHex("#cfd8ff")
	end
	local s = spinPopup:FindFirstChild("Pop") :: UIScale
	if not s then
		s = Instance.new("UIScale")
		s.Name = "Pop"
		s.Parent = spinPopup
	end
	s.Scale = 1.15
	TweenService:Create(s, TweenInfo.new(0.25, Enum.EasingStyle.Back), { Scale = 1 }):Play()
	task.delay(2.6, function()
		if token == popupToken then
			spinPopup.Visible = false
		end
	end)
end

local function doSpin(auto: boolean?)
	if busy or not snap then
		return
	end
	if os.clock() - lastSpinClock < snap.Cooldown then
		return
	end
	busy = true
	lastSpinClock = os.clock()
	local ok, msg, res = request("Spin")
	busy = false
	if ok and res then
		task.spawn(showRoll, res, not auto)
	elseif msg and not auto then
		toast(msg, "#ff8a96")
	end
end

local spinPanel = hud:WaitForChild("SpinPanel")
onClick(spinPanel:FindFirstChild("SpinButton"), function()
	doSpin(false)
end)
onClick(spinPanel:FindFirstChild("AutoButton"), function()
	if snap then
		result(request("SetAuto", not snap.Data.AutoSpin))
	end
end)

Remotes.Rolled.OnClientEvent:Connect(function(res)
	showRoll(res, true)
end)

-- ------------------------------------------------------------------ HUD buttons
local top = hud:WaitForChild("TopBar")
onClick(top:FindFirstChild("ShopTab"), function()
	open("ShopWindow")
end)
onClick(top:FindFirstChild("UpgradesTab"), function()
	open("UpgradesWindow")
end)
onClick(top:FindFirstChild("BaseTab"), function()
	closeWindows()
	request("Teleport")
end)

local left = hud:WaitForChild("LeftMenu")
onClick(left:FindFirstChild("DailyButton"), function()
	open("DailyWindow")
end)
onClick(left:FindFirstChild("ShopButton"), function()
	open("ShopWindow")
end)
onClick(left:FindFirstChild("PassButton"), function()
	open("PassWindow")
end)
onClick(left:FindFirstChild("RebirthButton"), function()
	open("RebirthWindow")
end)
onClick(left:FindFirstChild("IndexButton"), function()
	open("IndexWindow")
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

local stats = hud:WaitForChild("Stats")
onClick(stats:FindFirstChild("MoneyRow"):FindFirstChild("AddMoneyButton"), function()
	open("ShopWindow")
end)

local levelBar = hud:WaitForChild("LevelBar")
for _, k in { "Levels5", "Levels10", "Levels25" } do
	onClick(levelBar:FindFirstChild(k), function()
		result(request("Purchase", k))
	end)
end

-- shop window
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

-- daily
onClick(windows.DailyWindow.Header:FindFirstChild("ClaimAllButton"), function()
	result(request("ClaimDaily"))
end)
for d = 1, 7 do
	local card = windows.DailyWindow.Body:FindFirstChild("Day" .. d)
	onClick(card and card:FindFirstChild("Status"), function()
		result(request("ClaimDaily"))
	end)
end

-- pass
onClick(windows.PassWindow.Header:FindFirstChild("PremiumButton"), function()
	result(request("Purchase", "PremiumPass"))
end)
onClick(windows.PassWindow.Body.Bottom:FindFirstChild("ClaimButton"), function()
	result(request("ClaimPass"))
end)
onClick(windows.PassWindow.Body.Bottom:FindFirstChild("SkipButton"), function()
	result(request("Purchase", "PassSkip"))
end)

-- rebirth
onClick(windows.RebirthWindow.Body:FindFirstChild("RebirthButton"), function()
	result(request("Rebirth"))
end)
onClick(windows.RebirthWindow.Body:FindFirstChild("SkipButton"), function()
	result(request("Purchase", "SkipRebirth"))
end)

-- index tabs
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

-- upgrades
local selectedUpgrade = "Root"
local tree = windows.UpgradesWindow.Body.Tree
local info = windows.UpgradesWindow.Body.Info
local refreshAll -- forward
for _, u in GameData.Upgrades do
	onClick(tree:FindFirstChild("Node_" .. u.id), function()
		selectedUpgrade = u.id
		refreshAll()
	end)
end
onClick(info:FindFirstChild("BuyButton"), function()
	result(request("BuyUpgrade", selectedUpgrade))
end)

-- car shop (with 3D previews)
local carGrid = windows.CarShopWindow.Body.Grid
for _, c in GameData.Cars do
	local card = carGrid:FindFirstChild("Car_" .. c.id)
	if card then
		local vp = card:FindFirstChild("Viewport") :: ViewportFrame
		local model = Assets.Cars:FindFirstChild(c.id)
		if vp and model then
			local clone = model:Clone()
			clone.Parent = vp
			local cam = Instance.new("Camera")
			cam.FieldOfView = 40
			cam.CFrame = CFrame.lookAt(Vector3.new(-14, 9, -16), Vector3.new(0, 3, 0))
			cam.Parent = vp
			vp.CurrentCamera = cam
		end
		onClick(card:FindFirstChild("PriceButton"), function()
			result(request("BuyCar", c.id))
		end)
	end
end

-- styles
for _, s in GameData.Styles do
	local card = windows.StyleShopWindow.Body:FindFirstChild("Style_" .. s.id)
	onClick(card and card:FindFirstChild("PriceButton"), function()
		result(request("BuyStyle", s.id))
	end)
end

-- potions
for _, p in GameData.Potions do
	local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id)
	onClick(card and card:FindFirstChild("BuyButton"), function()
		result(request("BuyPotion", p.id))
	end)
end

-- lucky blocks
for _, b in GameData.LuckyBlocks do
	local card = windows.LuckyShopWindow.Body:FindFirstChild("Lucky_" .. b.id)
	if card then
		onClick(card:FindFirstChild("BuyButton"), function()
			result(request("BuyLucky", b.id))
		end)
		onClick(card:FindFirstChild("OpenButton"), function()
			local ok, msg, res = request("OpenLucky", b.id)
			if ok and res then
				closeWindows()
				showRoll(res, true)
			else
				result(ok, msg)
			end
		end)
	end
end

-- world prompts: shops on the hub and the spin machine on your plot
local SHOP_WINDOWS = {
	Potions = "PotionShopWindow",
	LuckyBlocks = "LuckyShopWindow",
	Cars = "CarShopWindow",
	Styles = "StyleShopWindow",
}
ProximityPromptService.PromptTriggered:Connect(function(prompt)
	local holder = prompt.Parent
	if not holder then
		return
	end
	local shop = holder:GetAttribute("Shop")
	if shop and SHOP_WINDOWS[shop] then
		open(SHOP_WINDOWS[shop])
		return
	end
	local plot: Instance? = holder
	while plot and not plot:GetAttribute("PlotIndex") do
		plot = plot.Parent
	end
	if holder.Parent and holder.Parent.Name == "SpinMachine" then
		if plot and plot:GetAttribute("OwnerId") == player.UserId then
			doSpin(false)
		else
			toast("This is not your plot!", "#ff8a96")
		end
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
	local moneyRow = stats:FindFirstChild("MoneyRow")
	moneyRow.Money.Text = "$" .. Format.commas(cash)
	stats.RebirthCount.Text = tostring(data.Rebirths)
	stats.FriendBoost.Text = "Friend Boost: +" .. math.floor(Stats.friendBoost(snap.Friends) * 100) .. "%"
	levelBar.Multiplier.Text = Format.mult(snap.MoneyMult) .. " Multiplier"
	local need = Stats.xpForLevel(data.Level)
	levelBar.Bar.Fill.Size = UDim2.fromScale(math.clamp(data.XP / need, 0, 1), 1)
	levelBar.Bar.LevelText.Text = "Level " .. data.Level
	levelBar.Bar.XPText.Text = data.XP .. "/" .. need .. " XP"
	local boosts = hud.Boosts
	local style = Stats.Styles[data.EquippedStyle]
	local additive = 1 + Stats.upgradeTotal(data, "Money") + (style and style.bonus or 0)
		+ Stats.friendBoost(snap.Friends)
	boosts.MoneyBoost.Value.Text = Format.mult(additive * Stats.potionMult(data, "Money")
		* (if data.Passes.X2Money then 2 else 1))
	boosts.RebirthBoost.Value.Text = Format.mult(Stats.rebirthMult(data.Rebirths))
	boosts.LuckBoost.Value.Text = Format.mult(snap.Luck)
	spinPanel.LuckLabel.Text = "🍀 Luck " .. Format.mult(snap.Luck)
	spinPanel.SlotsLabel.Text = "Track " .. #snap.Track .. "/" .. snap.Slots
	local auto = spinPanel.AutoButton
	setPreset(auto, if data.AutoSpin then "green" else "gray")
	auto.Sub.Text = if data.AutoSpin then "ON" else "OFF"
	right.X2MoneyButton.Sub.Text = if data.Passes.X2Money then "OWNED"
		else "\u{E002}" .. GameData.Products.Gamepasses.X2Money.price
	right.X2LuckButton.Sub.Text = if data.Passes.X2Luck then "OWNED"
		else "\u{E002}" .. GameData.Products.Gamepasses.X2Luck.price
	right.StarterPackButton.Visible = not data.StarterPack
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
			card.Known.Count.Text = "x" .. (data.Parts[p.id] or 0)
		end
	end
	windows.IndexWindow.Counter.Text = found .. "/" .. #GameData.Pieces .. " Found"
	applyIndexFilter()
end

local function refreshPass()
	local data = snap.Data
	local track = windows.PassWindow.Body.Track
	for _, entry in GameData.Pass do
		local col = track:FindFirstChild("Level_" .. entry.level)
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

local function refreshRebirth()
	local data = snap.Data
	local body = windows.RebirthWindow.Body
	local cash = player:GetAttribute("Cash") or data.Cash
	body.Current.Title.Text = "Rebirth " .. data.Rebirths
	body.Current.Value.Text = "X" .. Stats.rebirthMult(data.Rebirths) .. " Money"
	body.Next.Title.Text = "Rebirth " .. (data.Rebirths + 1)
	body.Next.Value.Text = "X" .. Stats.rebirthMult(data.Rebirths + 1) .. " Money"
	local req = body.Requirements
	req.ReqText.Text = "Have " .. Format.money(snap.RebirthCost) .. " (resets cash and track pieces)"
	req.Bar.Fill.Size = UDim2.fromScale(math.clamp(cash / snap.RebirthCost, 0, 1), 1)
	req.Bar.Text.Text = Format.money(cash) .. " / " .. Format.money(snap.RebirthCost)
end

local function refreshUpgrades()
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
				stroke.Color = if u.id == selectedUpgrade then Color3.fromHex("#ffffff")
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
	local u = Stats.Upgrades[selectedUpgrade]
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
	for _, b in GameData.LuckyBlocks do
		local card = windows.LuckyShopWindow.Body:FindFirstChild("Lucky_" .. b.id)
		if card then
			card.OwnedText.Text = "Owned: " .. (data.LuckyInv[b.id] or 0)
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
	-- potion cards + HUD timers
	local holder = hud.ActivePotions
	for _, p in GameData.Potions do
		local left = potionLeft(p.effect)
		local card = windows.PotionShopWindow.Body:FindFirstChild("Potion_" .. p.id)
		if card then
			card.TimerText.Text = if left > 0 then "Active: " .. Format.time(left) else ""
		end
		local t = holder:FindFirstChild(p.effect)
		if left > 0 then
			if not t then
				t = templates.PotionTimer:Clone()
				t.Name = p.effect
				t.Icon.Text = p.icon
				t.Parent = holder
			end
			t.Time.Text = Format.time(left)
		elseif t then
			t:Destroy()
		end
	end
	refreshDaily()
	-- spin cooldown
	local cd = snap.Cooldown
	local frac = math.clamp((os.clock() - lastSpinClock) / cd, 0, 1)
	spinPanel.CooldownBar.Fill.Size = UDim2.fromScale(frac, 1)
	spinPanel.SpinButton.Cooldown.Size = UDim2.fromScale(1, 1 - frac)
end

function refreshAll()
	if not snap then
		return
	end
	refreshHUD()
	refreshDaily()
	refreshIndex()
	refreshPass()
	refreshRebirth()
	refreshUpgrades()
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
		refreshRebirth()
	end
end)

Remotes.Notify.OnClientEvent:Connect(function(text, color)
	toast(text, color)
end)

-- floating "+$" text over the car
Remotes.Earned.OnClientEvent:Connect(function(amount: number, pos: Vector3)
	local cam = Workspace.CurrentCamera
	if not cam or (cam.CFrame.Position - pos).Magnitude > 500 then
		return
	end
	local anchor = Instance.new("Part")
	anchor.Anchored = true
	anchor.CanCollide = false
	anchor.CanQuery = false
	anchor.CanTouch = false
	anchor.Transparency = 1
	anchor.Size = Vector3.one
	anchor.CFrame = CFrame.new(pos + Vector3.new(0, 6, 0))
	local bb = Instance.new("BillboardGui")
	bb.Size = UDim2.fromOffset(240, 60)
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
	TweenService:Create(anchor, TweenInfo.new(1.2), { CFrame = anchor.CFrame + Vector3.new(0, 8, 0) }):Play()
	TweenService:Create(lbl, TweenInfo.new(1.2), { TextTransparency = 1 }):Play()
	TweenService:Create(st, TweenInfo.new(1.2), { Transparency = 1 }):Play()
	task.delay(1.25, function()
		anchor:Destroy()
	end)
end)

-- timers, cooldown and auto spin
local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if snap then
		local cd = snap.Cooldown
		local frac = math.clamp((os.clock() - lastSpinClock) / cd, 0, 1)
		spinPanel.CooldownBar.Fill.Size = UDim2.fromScale(frac, 1)
		spinPanel.SpinButton.Cooldown.Size = UDim2.fromScale(1, 1 - frac)
		if snap.Data.AutoSpin and frac >= 1 and not busy then
			task.spawn(doSpin, true)
		end
	end
	if acc >= 1 then
		acc = 0
		refreshTimers()
	end
end)

-- first load
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

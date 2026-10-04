-- Layout and content fixes applied on top of the Studio-made MainGui.
-- Safe to run again: every step checks what is already there.
-- Run from the repo root: lune run tools/lune/patch_ui.luau
local roblox = require("@lune/roblox")
local fs = require("@lune/fs")
local serde = require("@lune/serde")

local Instance = roblox.Instance
local UDim2, UDim, Vector2, Color3 = roblox.UDim2, roblox.UDim, roblox.Vector2, roblox.Color3
local Enum = roblox.Enum
local FREDOKA = roblox.Font.new("rbxasset://fonts/families/FredokaOne.json")

local PATH = "src/StarterGui/MainGui.rbxm"
local gui = roblox.deserializeModel(fs.readFile(PATH))[1]
local data = serde.decode("json", fs.readFile("src/ReplicatedStorage/Shared/GameData.json"))
local root = gui.Root
local hud = root.HUD
local windows = root.Windows

local TIER = {
	Common = Color3.fromRGB(184, 184, 184),
	Rare = Color3.fromRGB(63, 169, 255),
	Epic = Color3.fromRGB(181, 77, 255),
	Legendary = Color3.fromRGB(255, 179, 26),
	Mythical = Color3.fromRGB(255, 59, 107),
	Secret = Color3.fromRGB(240, 240, 255),
}

local function new(class, props, parent)
	local o = Instance.new(class)
	for k, v in props do
		o[k] = v
	end
	o.Parent = parent
	return o
end

local function short(n)
	for _, s in { { 1e9, "B" }, { 1e6, "M" }, { 1e3, "K" } } do
		if n >= s[1] then
			local v = n / s[1]
			local txt = if v >= 100 or v == math.floor(v) then string.format("%d", v) else string.format("%.1f", v)
			return "$" .. txt .. s[2]
		end
	end
	return "$" .. tostring(n)
end

local function mins(sec)
	return if sec % 60 == 0 then tostring(sec // 60) .. " min" else tostring(sec) .. " s"
end

-- ------------------------------------------------------------------ left column lower
hud.CashPanel.Position = UDim2.new(0, 28, 0, 150)
hud.IncomeLabel.Position = UDim2.new(0, 32, 0, 236)
hud.LeftMenu.Position = UDim2.new(0, 36, 0, 286)
-- 4 buttons x 140 + 3 gaps of 12 = 596 (ends at 882, above the stats row at 950)
for i, name in { "ShopButton", "IndexButton", "DailyButton", "PassButton" } do
	hud.LeftMenu[name].Position = UDim2.new(0, 0, 0, (i - 1) * 152)
end
hud.LeftMenu.Size = UDim2.new(0, 155, 0, 596)

-- ------------------------------------------------------------------ item icon helper
-- Hides the old atlas/emoji art of a slot and shows the rendered icon from GameData.
local function itemIcon(slot, image, size)
	for _, c in slot:GetDescendants() do
		if c.Name == "AtlasImage" then
			c:Destroy()
		end
	end
	for _, c in slot:GetChildren() do
		if c:IsA("UIStroke") or c:IsA("UIGradient") then
			c.Enabled = false
		elseif c:IsA("Frame") and string.sub(c.Name, 1, 3) == "Pip" then
			c.Visible = false
		elseif c:IsA("TextLabel") and c.Name == "Icon" then
			c.TextTransparency = 1
		end
	end
	slot.BackgroundTransparency = 1
	local img = slot:FindFirstChild("ItemIcon") or new("ImageLabel", { Name = "ItemIcon" }, slot)
	img.BackgroundTransparency = 1
	img.AnchorPoint = Vector2.new(0.5, 0.5)
	img.Position = UDim2.fromScale(0.5, 0.5)
	img.Size = UDim2.fromScale(size or 1.25, size or 1.25)
	img.ScaleType = Enum.ScaleType.Fit
	img.Image = image or ""
	img.ZIndex = slot.ZIndex + 1
	img.Active = false
	return img
end

-- ------------------------------------------------------------------ scrolling card grids
local function grid(window, prefix, items, fill, size)
	window.Size = size
	local body = window.Body
	local list = body:FindFirstChild("List")
	if not list then
		list = new("ScrollingFrame", {
			Name = "List",
			BackgroundTransparency = 1,
			BorderSizePixel = 0,
			Position = UDim2.new(0, 0, 0, 16),
			Size = UDim2.new(1, 0, 1, -24),
			CanvasSize = UDim2.new(0, 0, 0, 0),
			AutomaticCanvasSize = Enum.AutomaticSize.Y,
			ScrollingDirection = Enum.ScrollingDirection.Y,
			ScrollBarThickness = 12,
			ScrollBarImageColor3 = Color3.fromRGB(255, 255, 255),
			ScrollBarImageTransparency = 0.3,
			ZIndex = body.ZIndex,
		}, body)
		new("UIGridLayout", {
			CellSize = UDim2.fromOffset(232, 330),
			CellPadding = UDim2.fromOffset(16, 18),
			SortOrder = Enum.SortOrder.LayoutOrder,
			HorizontalAlignment = Enum.HorizontalAlignment.Center,
		}, list)
		new("UIPadding", {
			PaddingTop = UDim.new(0, 8),
			PaddingBottom = UDim.new(0, 18),
			PaddingLeft = UDim.new(0, 10),
			PaddingRight = UDim.new(0, 20),
		}, list)
	end
	local template
	for _, c in body:GetChildren() do
		if string.sub(c.Name, 1, #prefix) == prefix then
			c.Parent = list
		end
	end
	for _, c in list:GetChildren() do
		if string.sub(c.Name, 1, #prefix) == prefix then
			template = template or c
		end
	end
	for i, it in items do
		local card = list:FindFirstChild(prefix .. it.id)
		if not card then
			card = template:Clone()
			card.Name = prefix .. it.id
			card.Parent = list
		end
		card.LayoutOrder = i
		fill(card, it)
	end
end

grid(windows.DiceShopWindow, "Dice_", data.Dice, function(card, d)
	card.NameText.Text = d.name
	card.LuckText.Text = "🍀 x" .. string.format("%d", d.luck) .. " Luck Roll"
	card.OwnedText.Text = "Owned: 0"
	card.BuyButton.Label.Text = short(d.price)
	itemIcon(card.Die, d.image, 1.3)
	local stroke = card:FindFirstChild("Stroke")
	if stroke then
		stroke.Color = TIER[d.tier] or TIER.Common
	end
	local tag = card:FindFirstChild("TierTag") or new("TextLabel", { Name = "TierTag" }, card)
	tag.BackgroundTransparency = 1
	tag.Position = UDim2.new(0, 10, 0, 6)
	tag.Size = UDim2.new(1, -20, 0, 26)
	tag.FontFace = FREDOKA
	tag.TextScaled = true
	tag.TextXAlignment = Enum.TextXAlignment.Left
	tag.Text = string.upper(d.tier)
	tag.TextColor3 = TIER[d.tier] or TIER.Common
	tag.ZIndex = card.ZIndex + 3
	if not tag:FindFirstChildOfClass("UIStroke") then
		new("UIStroke", { Thickness = 2, Color = Color3.fromRGB(20, 20, 30) }, tag)
	end
end, UDim2.fromOffset(1290, 800))

grid(windows.PotionShopWindow, "Potion_", data.Potions, function(card, p)
	card.NameText.Text = p.name
	card.DescText.Text = p.desc .. " for " .. mins(p.duration)
	card.TimerText.Text = ""
	card.BuyButton.Label.Text = short(p.price)
	itemIcon(card.Bg, p.image, 1.3)
	local stroke = card:FindFirstChild("Stroke")
	if stroke then
		stroke.Color = TIER[p.tier] or TIER.Common
	end
end, UDim2.fromOffset(1290, 800))

-- ------------------------------------------------------------------ dice bar: owned dice only
local bar = hud.RollArea.DiceBar
bar.Size = UDim2.fromOffset(640, 78)
if not bar:FindFirstChildOfClass("UIListLayout") then
	new("UIListLayout", {
		FillDirection = Enum.FillDirection.Horizontal,
		HorizontalAlignment = Enum.HorizontalAlignment.Center,
		VerticalAlignment = Enum.VerticalAlignment.Center,
		SortOrder = Enum.SortOrder.LayoutOrder,
		Padding = UDim.new(0, 6),
	}, bar)
end
local chipTemplate = bar:FindFirstChild("Dice_Golden")
for i, d in data.Dice do
	local chip = bar:FindFirstChild("Dice_" .. d.id)
	if not chip then
		chip = chipTemplate:Clone()
		chip.Name = "Dice_" .. d.id
		chip.Parent = bar
	end
	chip.LayoutOrder = i
	itemIcon(chip, d.image, 1.05)
	chip.Count.ZIndex = chip.ZIndex + 3
end

-- ------------------------------------------------------------------ island styles: 3D previews
local styles = windows.StyleShopWindow
styles.Size = UDim2.fromOffset(1220, 830)
local order = {}
for i, s in data.Styles do
	order[s.id] = i
end
for _, card in styles.Body:GetChildren() do
	local id = string.sub(card.Name, 7)
	if string.sub(card.Name, 1, 6) == "Style_" and order[id] then
		local i = order[id] - 1
		card.Size = UDim2.fromOffset(270, 344)
		card.Position = UDim2.fromOffset(22 + (i % 4) * 296, 28 + (i // 4) * 366)
		local swatch = card.Swatch
		swatch.Size = UDim2.new(1, -20, 0, 34)
		swatch.Position = UDim2.new(0.5, 0, 0, 176)
		swatch.AnchorPoint = Vector2.new(0.5, 0)
		local vp = card:FindFirstChild("Preview")
		if not vp then
			vp = new("ViewportFrame", { Name = "Preview" }, card)
		end
		vp.BackgroundTransparency = 1
		vp.Position = UDim2.new(0.5, 0, 0, 8)
		vp.AnchorPoint = Vector2.new(0.5, 0)
		vp.Size = UDim2.new(1, -16, 0, 166)
		vp.Ambient = Color3.fromRGB(190, 200, 215)
		vp.LightColor = Color3.fromRGB(255, 250, 240)
		vp.LightDirection = roblox.Vector3.new(-1, -1.4, -0.6)
		vp.ZIndex = card.ZIndex + 1
		card.NameText.Position = UDim2.new(0, 4, 0, 214)
		card.BonusText.Position = UDim2.new(0, 4, 0, 250)
	end
end

-- ------------------------------------------------------------------ settings (music / sfx / effects)
local settings = hud:FindFirstChild("SettingsBar")
if not settings then
	settings = new("Frame", {
		Name = "SettingsBar",
		BackgroundTransparency = 1,
		Position = UDim2.new(0, 352, 0, 158),
		Size = UDim2.fromOffset(222, 66),
	}, hud)
	new("UIListLayout", {
		FillDirection = Enum.FillDirection.Horizontal,
		Padding = UDim.new(0, 10),
		SortOrder = Enum.SortOrder.LayoutOrder,
	}, settings)
	for i, def in { { "MusicToggle", "🎵" }, { "SfxToggle", "🔊" }, { "VfxToggle", "✨" } } do
		local b = new("TextButton", {
			Name = def[1],
			LayoutOrder = i,
			Size = UDim2.fromOffset(66, 66),
			BackgroundColor3 = Color3.fromRGB(40, 46, 70),
			BackgroundTransparency = 0.15,
			AutoButtonColor = false,
			Text = def[2],
			TextScaled = true,
			FontFace = FREDOKA,
			TextColor3 = Color3.fromRGB(255, 255, 255),
		}, settings)
		new("UICorner", { CornerRadius = UDim.new(0, 18) }, b)
		new("UIStroke", {
			Name = "Stroke",
			Thickness = 3,
			Color = Color3.fromRGB(255, 255, 255),
			Transparency = 0.2,
			ApplyStrokeMode = Enum.ApplyStrokeMode.Border,
		}, b)
		new("UIPadding", {
			PaddingTop = UDim.new(0, 12),
			PaddingBottom = UDim.new(0, 12),
			PaddingLeft = UDim.new(0, 12),
			PaddingRight = UDim.new(0, 12),
		}, b)
		local off = new("Frame", {
			Name = "Off",
			BackgroundColor3 = Color3.fromRGB(255, 70, 90),
			BorderSizePixel = 0,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5, 0.5),
			Size = UDim2.new(1.25, 0, 0, 6),
			Rotation = -40,
			Visible = false,
			ZIndex = b.ZIndex + 2,
		}, b)
		new("UICorner", { CornerRadius = UDim.new(1, 0) }, off)
	end
end

fs.writeFile(PATH, roblox.serializeModel({ gui }))
print("patched", PATH)

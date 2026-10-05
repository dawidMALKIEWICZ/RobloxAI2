-- Extra life for the whole interface (presentation only). Wires itself onto the existing UI:
--   * every button: light sweep on hover
--   * shop / index / build cards: hover lift + tilt, shimmering rarity borders on rare items
--   * window header icons wobble, close buttons spin on hover
--   * roll button: die spin + squash on press, spinning ring while Auto Roll is on
--   * dice chips hop when hovered, rare feed rows slide in, potion timers pulse and blink
--   * cash panel gleams whenever money comes in
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local UIFX = {}
UIFX.__index = UIFX

local RARE = {
	Epic = { Color3.fromRGB(198, 83, 255), Color3.fromRGB(255, 255, 255) },
	Legendary = { Color3.fromRGB(255, 204, 44), Color3.fromRGB(255, 255, 220) },
	Mythical = { Color3.fromRGB(255, 60, 126), Color3.fromRGB(255, 200, 230) },
	Secret = { Color3.fromRGB(255, 80, 80), Color3.fromRGB(80, 200, 255) },
}

local function tween(o, t, props, style, dir)
	local tw = TweenService:Create(o, TweenInfo.new(t, style or Enum.EasingStyle.Quad, dir or Enum.EasingDirection.Out), props)
	tw:Play()
	return tw
end

local function scaleFor(o: Instance, name: string): UIScale
	local s = o:FindFirstChild(name) :: UIScale
	if not s then
		s = Instance.new("UIScale")
		s.Name = name
		s.Parent = o
	end
	return s
end

function UIFX.new(gui: ScreenGui, gameData)
	local self = setmetatable({ Gui = gui, Root = gui:WaitForChild("Root"), Data = gameData, Shimmers = {}, Spinners = {},
		Connections = {}, T = 0 }, UIFX)
	self:WireButtons()
	self:WireCards()
	self:WireWindows()
	self:WireRoll()
	self:WireFeed()
	table.insert(self.Connections, RunService.RenderStepped:Connect(function(dt)
		self:Step(dt)
	end))
	gui.Destroying:Connect(function()
		for _, c in self.Connections do
			c:Disconnect()
		end
	end)
	return self
end

function UIFX:Connect(sig, fn)
	table.insert(self.Connections, sig:Connect(fn))
end

-- ------------------------------------------------------------------ buttons: hover light sweep
-- a white copy of an image with a moving bright band: a glint that follows the art's shape
function UIFX:Glint(img: ImageLabel)
	if img:FindFirstChild("Glint") then
		return img.Glint:FindFirstChildOfClass("UIGradient")
	end
	local g = img:Clone()
	g.Name = "Glint"
	for _, c in g:GetChildren() do
		c:Destroy()
	end
	g.ImageColor3 = Color3.new(1, 1, 1)
	g.Size = UDim2.fromScale(1, 1)
	g.Position = UDim2.fromScale(0.5, 0.5)
	g.AnchorPoint = Vector2.new(0.5, 0.5)
	g.ZIndex = img.ZIndex + 1
	g.Parent = img
	local grad = Instance.new("UIGradient")
	grad.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.42, 1),
		NumberSequenceKeypoint.new(0.5, 0.2), NumberSequenceKeypoint.new(0.58, 1), NumberSequenceKeypoint.new(1, 1) })
	grad.Rotation = 25
	grad.Offset = Vector2.new(-1.2, 0)
	grad.Parent = g
	return grad
end

function UIFX:Sweep(button: GuiObject)
	if button:GetAttribute("Sweep") or button.AbsoluteSize.X < 40 then
		return
	end
	local art = button:FindFirstChild("Art") or button:FindFirstChild("ItemIcon")
	if art and art:IsA("ImageLabel") then
		button:SetAttribute("Sweep", true)
		local grad = self:Glint(art)
		self:Connect(button.MouseEnter, function()
			grad.Offset = Vector2.new(-1.2, 0)
			tween(grad, 0.5, { Offset = Vector2.new(1.2, 0) }, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)
		end)
		return
	end
	if button.BackgroundTransparency > 0.6 then
		return   -- frameless icon buttons: no rectangle sweeping through empty space
	end
	button:SetAttribute("Sweep", true)
	local holder = Instance.new("Frame")
	holder.Name = "SweepClip"
	holder.BackgroundTransparency = 1
	holder.Size = UDim2.fromScale(1, 1)
	holder.ClipsDescendants = true
	holder.ZIndex = button.ZIndex + 4
	holder.Active = false
	holder.Parent = button
	local corner = button:FindFirstChildOfClass("UICorner")
	if corner then
		corner:Clone().Parent = holder
	end
	local bar = Instance.new("Frame")
	bar.Name = "Sweep"
	bar.BorderSizePixel = 0
	bar.BackgroundColor3 = Color3.new(1, 1, 1)
	bar.BackgroundTransparency = 0.55
	bar.AnchorPoint = Vector2.new(0.5, 0.5)
	bar.Size = UDim2.new(0, 26, 2.2, 0)
	bar.Position = UDim2.new(-0.3, 0, 0.5, 0)
	bar.Rotation = 20
	bar.ZIndex = button.ZIndex + 4
	bar.Visible = false
	bar.Parent = holder
	local g = Instance.new("UIGradient")
	g.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.5, 0),
		NumberSequenceKeypoint.new(1, 1) })
	g.Parent = bar
	self:Connect(button.MouseEnter, function()
		bar.Visible = true
		bar.Position = UDim2.new(-0.3, 0, 0.5, 0)
		tween(bar, 0.45, { Position = UDim2.new(1.3, 0, 0.5, 0) }, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)
	end)
end

function UIFX:WireButtons()
	local function try(d)
		if d:IsA("GuiButton") then
			task.defer(function()
				if d.Parent then
					self:Sweep(d)
				end
			end)
		end
	end
	for _, d in self.Root:GetDescendants() do
		try(d)
	end
	self:Connect(self.Root.DescendantAdded, try)
end

-- ------------------------------------------------------------------ cards
local function tierOf(self, name: string): string?
	local kind, id = string.match(name, "^(%a+)_(.+)$")
	local list = kind == "Dice" and self.Data.Dice or kind == "Potion" and self.Data.Potions
		or kind == "Piece" and self.Data.Pieces or kind == "Item" and self.Data.Pieces or nil
	if not list then
		return nil
	end
	for _, it in list do
		if it.id == id then
			return it.tier
		end
	end
	return nil
end

function UIFX:Card(card: GuiObject)
	if card:GetAttribute("CardFX") then
		return
	end
	card:SetAttribute("CardFX", true)
	local lift = scaleFor(card, "HoverLift")
	self:Connect(card.MouseEnter, function()
		tween(lift, 0.18, { Scale = 1.05 }, Enum.EasingStyle.Back)
		tween(card, 0.18, { Rotation = (math.random() < 0.5 and -1 or 1) * 1.6 })
	end)
	self:Connect(card.MouseLeave, function()
		tween(lift, 0.2, { Scale = 1 })
		tween(card, 0.25, { Rotation = 0 }, Enum.EasingStyle.Back)
	end)
	local tier = tierOf(self, card.Name)
	local cols = tier and RARE[tier]
	local stroke = card:FindFirstChild("Stroke") or card:FindFirstChildOfClass("UIStroke")
	if cols and stroke and stroke:IsA("UIStroke") then
		-- shimmering rarity border
		stroke.Thickness = math.max(stroke.Thickness, 4)
		local g = stroke:FindFirstChild("Shimmer") or Instance.new("UIGradient")
		g.Name = "Shimmer"
		if tier == "Secret" then
			g.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 80, 80)),
				ColorSequenceKeypoint.new(0.25, Color3.fromRGB(255, 220, 60)), ColorSequenceKeypoint.new(0.5, Color3.fromRGB(80, 255, 140)),
				ColorSequenceKeypoint.new(0.75, Color3.fromRGB(70, 190, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(200, 90, 255)) })
		else
			g.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, cols[1]), ColorSequenceKeypoint.new(0.5, cols[2]),
				ColorSequenceKeypoint.new(1, cols[1]) })
		end
		stroke.Color = Color3.new(1, 1, 1)
		g.Parent = stroke
		table.insert(self.Shimmers, { g = g, speed = tier == "Epic" and 60 or tier == "Legendary" and 90 or 140 })
	end
end

function UIFX:WireCards()
	local function try(d)
		local n = d.Name
		local isCard = d:IsA("GuiObject") and (n:match("^Dice_") or n:match("^Potion_") or n:match("^Car_")
			or n:match("^Style_") or n:match("^Piece_") or n:match("^Item_"))
		if isCard and d.Parent and d.Parent.Name ~= "DiceBar" and d.Parent.Name ~= "Bg" then
			self:Card(d)
		end
	end
	for _, d in self.Root:GetDescendants() do
		try(d)
	end
	self:Connect(self.Root.DescendantAdded, function(d)
		task.defer(try, d)
	end)
	-- dice chips hop
	local bar = self.Root.HUD.RollArea:FindFirstChild("DiceBar")
	if bar then
		for _, chip in bar:GetChildren() do
			if chip:IsA("GuiButton") then
				local s = scaleFor(chip, "Hop")
				self:Connect(chip.MouseEnter, function()
					tween(s, 0.12, { Scale = 1.18 }, Enum.EasingStyle.Back)
					tween(chip, 0.12, { Rotation = 8 })
				end)
				self:Connect(chip.MouseLeave, function()
					tween(s, 0.2, { Scale = 1 })
					tween(chip, 0.3, { Rotation = 0 }, Enum.EasingStyle.Elastic)
				end)
			end
		end
	end
end

-- ------------------------------------------------------------------ windows
function UIFX:WireWindows()
	for _, w in self.Root.Windows:GetChildren() do
		local header = w:FindFirstChild("Header")
		local icon = header and header:FindFirstChild("Icon")
		if icon and icon:IsA("GuiObject") then
			table.insert(self.Spinners, { obj = icon, kind = "wobble", phase = math.random() * 6 })
		end
	end
end

-- ------------------------------------------------------------------ roll button
function UIFX:WireRoll()
	local area = self.Root.HUD.RollArea
	local roll = area:FindFirstChild("RollButton")
	local die = roll and roll:FindFirstChild("Die")
	if not roll or not die then
		return
	end
	local squash = scaleFor(die, "Squash")
	self:Connect(roll.MouseButton1Down, function()
		tween(squash, 0.08, { Scale = 0.86 })
	end)
	self:Connect(roll.Activated, function()
		squash.Scale = 1.15
		tween(squash, 0.35, { Scale = 1 }, Enum.EasingStyle.Elastic)
		die.Rotation = -25
		tween(die, 0.5, { Rotation = 0 }, Enum.EasingStyle.Elastic)
	end)
	self.AutoRings = {}
end

function UIFX:SetAuto(on: boolean)
	for _, r in self.AutoRings or {} do
		r.Visible = on
	end
end

-- ------------------------------------------------------------------ rare feed
function UIFX:WireFeed()
	local feed = self.Root.HUD:FindFirstChild("RareFeed")
	if not feed then
		return
	end
	local row1 = feed:FindFirstChild("Row1")
	if not row1 then
		return
	end
	local base = row1.Position
	self.FeedIn = function()
		row1.Position = base + UDim2.fromOffset(160, 0)
		tween(row1, 0.4, { Position = base }, Enum.EasingStyle.Back)
		local glow = Instance.new("Frame")
		glow.BackgroundColor3 = Color3.new(1, 1, 1)
		glow.BackgroundTransparency = 0.3
		glow.BorderSizePixel = 0
		glow.Size = UDim2.fromScale(1, 1)
		glow.ZIndex = row1.ZIndex + 3
		glow.Parent = row1
		tween(glow, 0.6, { BackgroundTransparency = 1 })
		game:GetService("Debris"):AddItem(glow, 0.65)
	end
end

-- money in: a gleam runs over the cash panel
function UIFX:CashGleam()
	local panel = self.Root.HUD:FindFirstChild("CashPanel")
	if not panel or (self.LastGleam and os.clock() - self.LastGleam < 0.8) then
		return
	end
	self.LastGleam = os.clock()
	self:Sweep(panel)
	local clip = panel:FindFirstChild("SweepClip")
	local bar = clip and clip:FindFirstChild("Sweep")
	if bar then
		bar.Visible = true
		bar.Position = UDim2.new(-0.3, 0, 0.5, 0)
		tween(bar, 0.5, { Position = UDim2.new(1.3, 0, 0.5, 0) })
	end
end

-- ------------------------------------------------------------------ per frame
function UIFX:Step(dt: number)
	self.T += dt
	local t = self.T
	for _, s in self.Shimmers do
		if s.g.Parent then
			s.g.Rotation = (t * s.speed) % 360
		end
	end
	for _, s in self.Spinners do
		if s.obj.Parent and s.obj.Visible then
			s.obj.Rotation = math.sin(t * 2 + s.phase) * 7
		end
	end
	for i, r in self.AutoRings or {} do
		if r.Visible then
			r.Rotation = (t * (i == 1 and 120 or -70)) % 360
		end
	end
	-- potion timers: gentle pulse, fast blink in the last 10 seconds
	local holder = self.Root.HUD:FindFirstChild("ActivePotions")
	if holder then
		for _, tm in holder:GetChildren() do
			if tm:IsA("GuiObject") then
				local s = scaleFor(tm, "Pulse")
				local txt = tm:FindFirstChild("Time")
				local secs = txt and tonumber(string.match(txt.Text, "^0?:?(%d+)$")) or 99
				local short = txt and string.match(txt.Text, "^0:%d%d$") and secs <= 10
				s.Scale = short and (1 + math.abs(math.sin(t * 9)) * 0.12) or (1 + math.sin(t * 2.5) * 0.03)
			end
		end
	end
end

return UIFX

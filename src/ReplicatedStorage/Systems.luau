-- Client side of the newer systems:
--   * Dice Fusion window (3 dice -> 1 better die) with a full fusion animation
--   * "Welcome back" offline earnings popup
--   * Second floor: the Build panel floor button, the floating build grid, see-through upper
--     floor while building below, and the animated construction of towers, girders and pillars
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Workspace = game:GetService("Workspace")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local GameData = require(Shared:WaitForChild("GameData"))
local Stats = require(Shared:WaitForChild("Stats"))
local Format = require(Shared:WaitForChild("Format"))

local Systems = {}
Systems.__index = Systems

local FONT = Font.new("rbxasset://fonts/families/FredokaOne.json", Enum.FontWeight.Bold)
local RING = "rbxassetid://134711977820804"
local GLOW = "rbxassetid://82400724728274"
local INK = Color3.fromHex("#15131f")
local PAD_Y = 0.3

local function tween(obj: Instance, t: number, props: { [string]: any }, style: Enum.EasingStyle?,
	dir: Enum.EasingDirection?): Tween
	local tw = TweenService:Create(obj, TweenInfo.new(t, style or Enum.EasingStyle.Quad,
		dir or Enum.EasingDirection.Out), props)
	tw:Play()
	return tw
end

local function new(class: string, props: { [string]: any }, children: { Instance }?): any
	local o = Instance.new(class)
	for k, v in props do
		if k ~= "Parent" then
			(o :: any)[k] = v
		end
	end
	if children then
		for _, c in children do
			c.Parent = o
		end
	end
	if props.Parent then
		o.Parent = props.Parent
	end
	return o
end

local function corner(r: number?): UICorner
	return new("UICorner", { CornerRadius = UDim.new(0, r or 16) })
end

local function stroke(color: Color3?, thick: number?): UIStroke
	return new("UIStroke", { Color = color or INK, Thickness = thick or 3,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Border })
end

local function textStroke(thick: number?): UIStroke
	return new("UIStroke", { Color = INK, Thickness = thick or 3 })
end

local function label(props: { [string]: any }): TextLabel
	local l = new("TextLabel", {
		BackgroundTransparency = 1,
		FontFace = FONT,
		TextScaled = true,
		TextColor3 = Color3.new(1, 1, 1),
	}, { textStroke(props.StrokeThickness) })
	props.StrokeThickness = nil
	for k, v in props do
		(l :: any)[k] = v
	end
	return l
end

local function gradient(c1: Color3, c2: Color3, rot: number?): UIGradient
	return new("UIGradient", { Color = ColorSequence.new(c1, c2), Rotation = rot or 90 })
end

-- a cloned button carries the "already wired" markers of its source; clear them so the
-- hover/press effects get wired again for the copy
local function freshClone<T>(obj: T & Instance): T
	local o = (obj :: any):Clone()
	for _, d in o:GetDescendants() do
		if d.Name == "SweepClip" or d.Name == "HoverHighlight" then
			d:Destroy()
		end
	end
	o:SetAttribute("VFXBound", nil)
	o:SetAttribute("Sweep", nil)
	for _, d in o:GetDescendants() do
		d:SetAttribute("VFXBound", nil)
		d:SetAttribute("Sweep", nil)
	end
	return o
end

local function tierColor(tier: string): Color3
	local t = Stats.Tiers[tier]
	return if t then Color3.fromHex(t.color) else Color3.new(1, 1, 1)
end

local function diceColor(d): Color3
	if d.color == "rainbow" then
		return Color3.fromHex("#ff6fd8")
	end
	return Color3.fromHex(d.color)
end

-- die picture: the shop icon when it exists, a coloured rounded square with pips otherwise
local function dieIcon(d, size: UDim2, parent: Instance?): GuiObject
	if d.image then
		return new("ImageLabel", { Name = "DieIcon", BackgroundTransparency = 1, Image = d.image,
			Size = size, AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5),
			ScaleType = Enum.ScaleType.Fit, Parent = parent })
	end
	local f = new("Frame", { Name = "DieIcon", BackgroundColor3 = diceColor(d), Size = size,
		AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Parent = parent },
		{ corner(18), stroke(INK, 3) })
	new("UIAspectRatioConstraint", { Parent = f })
	for _, p in { { 0.28, 0.28 }, { 0.72, 0.28 }, { 0.5, 0.5 }, { 0.28, 0.72 }, { 0.72, 0.72 } } do
		new("Frame", { BackgroundColor3 = Color3.new(1, 1, 1), Size = UDim2.fromScale(0.16, 0.16),
			AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(p[1], p[2]), Parent = f },
			{ corner(99) })
	end
	return f
end

local function diceIndex(id: string): number?
	for i, d in GameData.Dice do
		if d.id == id then
			return i
		end
	end
	return nil
end

Systems.freshClone = freshClone

-- ------------------------------------------------------------------ construction
function Systems.new(ctx)
	local self = setmetatable({}, Systems)
	self.ctx = ctx
	self.gui = ctx.gui
	self.root = ctx.gui:WaitForChild("Root")
	self.vfx = ctx.vfx
	self.worldFX = ctx.worldFX
	self.snap = nil
	self.fuseId = nil
	self.fusing = false
	self.buildFloor = 0
	self.buildOpen = false
	self.floorConfirm = 0
	self.screen = new("ScreenGui", { Name = "TrackRNGSystems", ResetOnSpawn = false, IgnoreGuiInset = true,
		DisplayOrder = (ctx.gui.DisplayOrder or 0) + 4, ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
		Parent = ctx.gui.Parent })
	self.screenScale = new("UIScale", { Parent = self.screen })
	self:BuildFusionWindow()
	self:BuildFloorButton()
	self:HookConstruction()
	return self
end

-- ------------------------------------------------------------------ dice fusion window
function Systems:BuildFusionWindow()
	local windows = self.root:WaitForChild("Windows")
	local shop = windows:WaitForChild("DiceShopWindow")
	local w = freshClone(shop)
	w.Name = "FusionWindow"
	w.Visible = false
	w.Size = UDim2.fromOffset(1060, 700)
	local list = w.Body:FindFirstChild("List")
	if list then
		list:Destroy()
	end
	for _, c in w:GetChildren() do
		if c.Name ~= "Body" and c.Name ~= "Header" and not c:IsA("UIBase") then
			c:Destroy()
		end
	end
	local header = w.Header
	header.Title.Text = "Dice Fusion"
	header.Icon.Text = "🔮"
	local atlas = header.Icon:FindFirstChild("AtlasImage")
	if atlas then
		atlas.Visible = false
	end
	w.Parent = windows
	self.window = w
	local body = w.Body

	-- left: the fusion machine
	local machine = new("Frame", { Name = "Machine", BackgroundColor3 = Color3.fromHex("#120f26"),
		Position = UDim2.fromOffset(24, 20), Size = UDim2.fromOffset(600, 572), ClipsDescendants = true,
		Parent = body }, { corner(22), stroke(Color3.fromHex("#5b3bd1"), 4),
		gradient(Color3.fromHex("#2a1f5c"), Color3.fromHex("#0d0a1f"), 90) })
	self.machine = machine
	local centre = UDim2.fromOffset(300, 250)
	self.centrePos = Vector2.new(300, 250)
	local halo = new("ImageLabel", { Name = "Halo", BackgroundTransparency = 1, Image = GLOW,
		AnchorPoint = Vector2.new(0.5, 0.5), Position = centre, Size = UDim2.fromOffset(420, 420),
		ImageColor3 = Color3.fromHex("#8a5bff"), ImageTransparency = 0.55, Parent = machine })
	local ring1 = new("ImageLabel", { Name = "Ring1", BackgroundTransparency = 1, Image = RING,
		AnchorPoint = Vector2.new(0.5, 0.5), Position = centre, Size = UDim2.fromOffset(300, 300),
		ImageColor3 = Color3.fromHex("#b98bff"), ImageTransparency = 0.25, Parent = machine })
	local ring2 = new("ImageLabel", { Name = "Ring2", BackgroundTransparency = 1, Image = RING,
		AnchorPoint = Vector2.new(0.5, 0.5), Position = centre, Size = UDim2.fromOffset(190, 190),
		ImageColor3 = Color3.fromHex("#3bf6ff"), ImageTransparency = 0.35, Parent = machine })
	self.halo, self.ring1, self.ring2 = halo, ring1, ring2
	-- connecting energy lines from the slots to the core
	self.lines = {}
	self.slots = {}
	for i = 1, 3 do
		local a = math.rad(-90 + (i - 1) * 120)
		local pos = Vector2.new(300 + math.cos(a) * 185, 250 + math.sin(a) * 185)
		local line = new("Frame", { Name = "Line" .. i, BorderSizePixel = 0, AnchorPoint = Vector2.new(0, 0.5),
			BackgroundColor3 = Color3.fromHex("#b98bff"), BackgroundTransparency = 0.5,
			Position = UDim2.fromOffset(300, 250), Size = UDim2.fromOffset(185, 6),
			Rotation = math.deg(a), Parent = machine }, { corner(3) })
		new("UIGradient", { Transparency = NumberSequence.new(0.9, 0), Parent = line })
		self.lines[i] = line
		local slot = new("Frame", { Name = "Slot" .. i, BackgroundColor3 = Color3.fromHex("#241a4d"),
			AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromOffset(pos.X, pos.Y),
			Size = UDim2.fromOffset(132, 132), Parent = machine },
			{ corner(66), stroke(Color3.fromHex("#8a5bff"), 4) })
		self.slots[i] = { frame = slot, pos = pos, angle = a }
	end
	-- the core shows the die you will get
	local core = new("Frame", { Name = "Core", BackgroundTransparency = 1, AnchorPoint = Vector2.new(0.5, 0.5),
		Position = centre, Size = UDim2.fromOffset(130, 130), Parent = machine })
	self.core = core
	self.coreScale = new("UIScale", { Parent = core })
	self.coreQ = label({ Name = "Question", Text = "?", Size = UDim2.fromScale(0.6, 0.6),
		AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), ZIndex = 5,
		TextColor3 = Color3.fromHex("#ffe14d"), Parent = core })
	self.resultName = label({ Name = "ResultName", Text = "", Size = UDim2.fromOffset(560, 54),
		AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.fromOffset(300, 448), Parent = machine })
	self.resultInfo = label({ Name = "ResultInfo", Text = "", Size = UDim2.fromOffset(540, 34),
		AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.fromOffset(300, 504),
		TextColor3 = Color3.fromHex("#cfc4ff"), StrokeThickness = 2, Parent = machine })
	self.flash = new("Frame", { Name = "Flash", BackgroundColor3 = Color3.new(1, 1, 1), BackgroundTransparency = 1,
		Size = UDim2.fromScale(1, 1), ZIndex = 30, Parent = machine })

	-- right: picker + fuse button
	local picker = new("ScrollingFrame", { Name = "Picker", BackgroundColor3 = Color3.fromHex("#0f1830"),
		BackgroundTransparency = 0.25, Position = UDim2.fromOffset(644, 20), Size = UDim2.fromOffset(392, 372),
		ScrollBarThickness = 8, CanvasSize = UDim2.new(), AutomaticCanvasSize = Enum.AutomaticSize.Y,
		BorderSizePixel = 0, Parent = body }, { corner(18), stroke(Color3.fromHex("#2b3b66"), 3) })
	new("UIGridLayout", { CellSize = UDim2.fromOffset(112, 128), CellPadding = UDim2.fromOffset(10, 10),
		SortOrder = Enum.SortOrder.LayoutOrder, HorizontalAlignment = Enum.HorizontalAlignment.Center,
		Parent = picker })
	new("UIPadding", { PaddingTop = UDim.new(0, 12), PaddingBottom = UDim.new(0, 12), Parent = picker })
	self.picker = picker
	self.chips = {}
	for i, d in GameData.Dice do
		local chip = new("TextButton", { Name = "Chip_" .. d.id, Text = "", AutoButtonColor = false,
			BackgroundColor3 = tierColor(d.tier):Lerp(Color3.fromHex("#0f1830"), 0.65), LayoutOrder = i,
			Parent = picker }, { corner(16) })
		local st = stroke(tierColor(d.tier), 3)
		st.Parent = chip
		local holder = new("Frame", { BackgroundTransparency = 1, Size = UDim2.fromOffset(84, 84),
			AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 6), Parent = chip })
		dieIcon(d, UDim2.fromScale(1, 1), holder)
		local count = label({ Name = "Count", Text = "x0", Size = UDim2.new(1, -8, 0, 30),
			Position = UDim2.new(0, 4, 1, -34), Parent = chip })
		chip.Activated:Connect(function()
			self:Select(d.id)
		end)
		self.chips[d.id] = { button = chip, count = count, stroke = st }
	end
	self.info = label({ Name = "Info", Text = "", Size = UDim2.fromOffset(392, 66), Position = UDim2.fromOffset(644, 402),
		TextColor3 = Color3.fromHex("#dfe7ff"), StrokeThickness = 2, TextWrapped = true, Parent = body })
	local button = shop:FindFirstChild("BuyButton", true)
	local fuse: GuiButton
	if button then
		fuse = freshClone(button)
	else
		fuse = new("TextButton", { Text = "", BackgroundColor3 = Color3.new(1, 1, 1) }, { corner(14), stroke(INK, 3),
			new("UIGradient", { Name = "Gradient", Rotation = 90 }), label({ Name = "Label", Size = UDim2.fromScale(1, 1) }) })
	end
	fuse.Name = "FuseButton"
	fuse.AnchorPoint = Vector2.new(0, 0)
	fuse.Position = UDim2.fromOffset(644, 488)
	fuse.Size = UDim2.fromOffset(392, 92)
	fuse.Parent = body
	self.fuseButton = fuse
	self.ctx.setPreset(fuse, "purple")
	self.ctx.setText(fuse, "FUSE")
	self.ctx.vfx:BindButton(fuse)
	fuse.Activated:Connect(function()
		self:Fuse()
	end)
	header.Close.Activated:Connect(self.ctx.closeWindows)
	w:GetPropertyChangedSignal("Visible"):Connect(function()
		if w.Visible then
			self.vfx:Window(w)
			self.vfx:BlurTo(if self.vfx.Quality == "Low" then 0 else 9, 0.25)
			self:Refresh()
		else
			self.vfx:Sound("WindowClose")
			local other = false
			for _, o in windows:GetChildren() do
				if o ~= w and o:IsA("GuiObject") and o.Visible and o.Name ~= "SkillsWindow" then
					other = true
				end
			end
			if not other then
				self.vfx:BlurTo(0, 0.25)
			end
		end
	end)
	-- idle motion: rings turn, the halo breathes, energy lines pulse
	RunService.RenderStepped:Connect(function(dt)
		if not w.Visible then
			return
		end
		local speed = if self.fusing then 9 else 1
		ring1.Rotation += dt * 40 * speed
		ring2.Rotation -= dt * 65 * speed
		local t = os.clock()
		if not self.fusing then
			halo.ImageTransparency = 0.55 + math.sin(t * 2) * 0.12
			for i, line in self.lines do
				line.BackgroundTransparency = 0.45 + math.sin(t * 4 + i * 2) * 0.25
			end
		end
	end)
end

function Systems:Open(id: string?)
	if id then
		self.fuseId = id
	end
	self.ctx.open("FusionWindow")
end

function Systems:Select(id: string)
	if self.fusing then
		return
	end
	self.fuseId = id
	self.vfx:Sound("Click", 1.1)
	self:Refresh()
end

-- picks a sensible default: the cheapest die you have enough of
function Systems:DefaultFuse(data): string?
	local need = GameData.Config.FuseCount or 3
	for i, d in GameData.Dice do
		if i < #GameData.Dice and (data.Dice[d.id] or 0) >= need then
			return d.id
		end
	end
	return GameData.Dice[1].id
end

function Systems:SetSlots(d, n: number)
	local need = GameData.Config.FuseCount or 3
	for i, slot in self.slots do
		for _, c in slot.frame:GetChildren() do
			if c.Name == "DieIcon" or c.Name == "Empty" then
				c:Destroy()
			end
		end
		if d and i <= math.min(n, need) then
			dieIcon(d, UDim2.fromOffset(104, 104), slot.frame)
			slot.frame.UIStroke.Color = tierColor(d.tier)
		else
			label({ Name = "Empty", Text = "+", Size = UDim2.fromScale(0.5, 0.5), AnchorPoint = Vector2.new(0.5, 0.5),
				Position = UDim2.fromScale(0.5, 0.5), TextTransparency = 0.6, Parent = slot.frame })
			slot.frame.UIStroke.Color = Color3.fromHex("#4a3a80")
		end
	end
end

function Systems:SetCore(d, reveal: boolean)
	for _, c in self.core:GetChildren() do
		if c.Name == "DieIcon" then
			c:Destroy()
		end
	end
	if d then
		local icon = dieIcon(d, UDim2.fromScale(1, 1), self.core)
		if not reveal then
			if icon:IsA("ImageLabel") then
				icon.ImageTransparency = 0.6
				icon.ImageColor3 = Color3.fromHex("#9c8cff")
			else
				icon.BackgroundTransparency = 0.6
			end
		end
	end
	self.coreQ.Visible = not reveal
end

function Systems:Refresh()
	local snap = self.snap
	if not snap or not self.window then
		return
	end
	local data = snap.Data
	local need = GameData.Config.FuseCount or 3
	-- shop cards + HUD chip
	for _, d in GameData.Dice do
		local chip = self.chips[d.id]
		local n = data.Dice[d.id] or 0
		chip.count.Text = "x" .. n
		chip.button.BackgroundTransparency = if n >= need then 0 else 0.55
		chip.stroke.Thickness = if d.id == self.fuseId then 5 else 3
		chip.stroke.Color = if d.id == self.fuseId then Color3.fromHex("#ffe14d") else tierColor(d.tier)
	end
	if self.fusing then
		return
	end
	if not self.fuseId then
		self.fuseId = self:DefaultFuse(data)
	end
	local index = diceIndex(self.fuseId or "") or 1
	local d = GameData.Dice[index]
	local nextD = GameData.Dice[index + 1]
	local n = data.Dice[d.id] or 0
	self:SetSlots(d, n)
	self:SetCore(nextD, false)
	if not nextD then
		self.resultName.Text = d.name .. " is the best!"
		self.resultInfo.Text = "It cannot be fused any further."
		self.info.Text = ""
		self.ctx.setPreset(self.fuseButton, "gray")
		self.ctx.setText(self.fuseButton, "MAXED")
		return
	end
	local jackpot = GameData.Dice[index + 2]
	self.resultName.Text = need .. "x " .. d.name .. "  →  " .. nextD.name
	self.resultName.TextColor3 = tierColor(nextD.tier)
	self.resultInfo.Text = "x" .. Format.short(nextD.luck) .. " luck roll"
		.. (if jackpot then "  •  " .. math.floor((GameData.Config.FuseJackpot or 0.1) * 100)
			.. "% JACKPOT: " .. jackpot.name else "")
	self.info.Text = "You have " .. n .. "/" .. need .. " " .. d.name
		.. (if n < need then "\nBuy more in the Dice Shop or win them in rewards!" else "")
	if n >= need then
		self.ctx.setPreset(self.fuseButton, "purple")
		self.ctx.setText(self.fuseButton, "FUSE  " .. need .. " → 1")
	else
		self.ctx.setPreset(self.fuseButton, "gray")
		self.ctx.setText(self.fuseButton, "NEED " .. need)
	end
end

function Systems:Fuse()
	if self.fusing or not self.snap or not self.fuseId then
		return
	end
	local id = self.fuseId
	local ok, msg, res = self.ctx.request("FuseDice", id)
	if not ok or type(res) ~= "table" then
		if msg then
			self.ctx.toast(msg, "#ff8a96")
		end
		return
	end
	self:PlayFusion(res)
end

-- three dice spiral into the core, the core overloads and the new die bursts out
function Systems:PlayFusion(res)
	local from = GameData.Dice[diceIndex(res.from) or 1]
	local to = GameData.Dice[diceIndex(res.to) or 1]
	local color = tierColor(to.tier)
	local vfx = self.vfx
	self.fusing = true
	self.fuseButton.Active = false
	self.ctx.setPreset(self.fuseButton, "gray")
	self.ctx.setText(self.fuseButton, "FUSING...")
	vfx:Sound("RollStart", 0.9)
	local flyers = {}
	for i, slot in self.slots do
		local icon = slot.frame:FindFirstChild("DieIcon")
		if icon then
			icon:Destroy()
		end
		local f = new("Frame", { BackgroundTransparency = 1, AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromOffset(slot.pos.X, slot.pos.Y), Size = UDim2.fromOffset(104, 104), ZIndex = 10,
			Parent = self.machine })
		dieIcon(from, UDim2.fromScale(1, 1), f)
		local trail = new("ImageLabel", { BackgroundTransparency = 1, Image = GLOW, ImageColor3 = diceColor(from),
			AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromScale(1.8, 1.8),
			ImageTransparency = 0.4, ZIndex = 9, Parent = f })
		flyers[i] = { frame = f, angle = slot.angle, trail = trail }
		slot.frame.UIStroke.Color = Color3.fromHex("#4a3a80")
	end
	tween(self.halo, 1.1, { ImageTransparency = 0, Size = UDim2.fromOffset(560, 560), ImageColor3 = color })
	tween(self.ring1, 1.1, { Size = UDim2.fromOffset(240, 240), ImageColor3 = color })
	tween(self.ring2, 1.1, { Size = UDim2.fromOffset(140, 140) })
	for _, line in self.lines do
		tween(line, 0.3, { BackgroundTransparency = 0, BackgroundColor3 = color })
	end
	local dur = 1.15
	local t0 = os.clock()
	local lastTick = 0
	local conn
	conn = RunService.RenderStepped:Connect(function()
		local t = math.clamp((os.clock() - t0) / dur, 0, 1)
		local k = t * t
		for i, fl in flyers do
			local a = fl.angle + k * math.pi * 3.2
			local r = 185 * (1 - k)
			fl.frame.Position = UDim2.fromOffset(self.centrePos.X + math.cos(a) * r, self.centrePos.Y + math.sin(a) * r)
			local s = 104 * (1 - 0.6 * k)
			fl.frame.Size = UDim2.fromOffset(s, s)
			fl.frame.Rotation = k * 540 + i * 40
			for _, line in self.lines do
				line.Size = UDim2.fromOffset(185 * (1 - k), 6)
			end
		end
		if t * 12 >= lastTick + 1 then
			lastTick += 1
			vfx:Sound("Tick", 0.9 + t * 0.9, 0.35)
		end
		if t >= 1 then
			conn:Disconnect()
		end
	end)
	vfx:CameraPunch(0.35, 1)
	task.wait(dur)
	for _, fl in flyers do
		fl.frame:Destroy()
	end
	-- overload: flash, shockwave, rays, the result pops out
	local abs = self.core.AbsolutePosition + self.core.AbsoluteSize / 2
	local guiInset = Vector2.zero
	local point = abs + guiInset
	self.flash.BackgroundTransparency = 0
	tween(self.flash, 0.5, { BackgroundTransparency = 1 })
	vfx:Shockwave(point, color, if res.jackpot then 3 else 2)
	local rank = ({ Common = 1, Rare = 2, Epic = 3, Legendary = 4, Mythical = 5, Secret = 6 })[to.tier] or 2
	vfx:Rays(point, color, math.max(rank, 3))
	vfx:UIBurst(point, color, vfx:Q(26 + rank * 4), 260)
	vfx:CameraPunch(0.6, 0.25)
	vfx:Sound(({ "Rare", "Rare", "Epic", "Legendary", "Mythical", "Secret" })[rank] or "Epic")
	self:SetCore(to, true)
	self.coreScale.Scale = 0.1
	tween(self.coreScale, 0.55, { Scale = 1.35 }, Enum.EasingStyle.Back)
	self.resultName.Text = (if res.jackpot then "JACKPOT!  " else "") .. string.upper(to.name) .. "!"
	self.resultName.TextColor3 = color
	self.resultInfo.Text = "x" .. Format.short(to.luck) .. " luck roll  •  it's in your dice bar"
	if res.jackpot then
		vfx:Banner("JACKPOT FUSION!", color, 0.9, UDim2.fromScale(0.5, 0.2), 1.6, true)
		vfx:Confetti(point, color, vfx:Q(60), false)
		vfx:ScreenFlash(color, 0.45)
	end
	-- the new die floats while the rings settle
	tween(self.halo, 0.8, { ImageTransparency = 0.45, Size = UDim2.fromOffset(460, 460) })
	tween(self.ring1, 0.8, { Size = UDim2.fromOffset(330, 330), ImageColor3 = color })
	tween(self.ring2, 0.8, { Size = UDim2.fromOffset(210, 210) })
	task.wait(1.6)
	tween(self.coreScale, 0.3, { Scale = 1 })
	for _, line in self.lines do
		line.Size = UDim2.fromOffset(185, 6)
		line.BackgroundColor3 = Color3.fromHex("#b98bff")
	end
	self.fusing = false
	self.fuseButton.Active = true
	self:Refresh()
end

-- ------------------------------------------------------------------ offline popup
function Systems:ShowOffline(info)
	if type(info) ~= "table" or type(info.amount) ~= "number" then
		return
	end
	local vfx = self.vfx
	local holder = new("Frame", { Name = "OfflinePopup", BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), ZIndex = 50, Active = true, Parent = self.screen })
	tween(holder, 0.3, { BackgroundTransparency = 0.45 })
	local rays = new("ImageLabel", { BackgroundTransparency = 1, Image = GLOW, ImageColor3 = Color3.fromHex("#ffd23f"),
		AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(900, 900),
		ImageTransparency = 1, ZIndex = 50, Parent = holder })
	tween(rays, 0.6, { ImageTransparency = 0.55 })
	local panel = new("Frame", { Name = "Panel", BackgroundColor3 = Color3.fromHex("#1c2b52"),
		AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(640, 440),
		ZIndex = 51, Parent = holder }, { corner(28), stroke(INK, 5),
		gradient(Color3.fromHex("#3b5bdb"), Color3.fromHex("#1a2448"), 90) })
	local scale = new("UIScale", { Scale = 0.2, Parent = panel })
	-- fit small screens
	local cam = Workspace.CurrentCamera
	local fit = if cam then math.min(1, cam.ViewportSize.Y / 560, cam.ViewportSize.X / 700) else 1
	tween(scale, 0.45, { Scale = fit }, Enum.EasingStyle.Back)
	local title = label({ Text = "WELCOME BACK!", Size = UDim2.new(1, -40, 0, 70), Position = UDim2.fromOffset(20, 22),
		ZIndex = 52, StrokeThickness = 5, Parent = panel })
	gradient(Color3.fromHex("#fff6b0"), Color3.fromHex("#ffb31a"), 90).Parent = title
	local hours = math.floor(info.away / 3600)
	local mins = math.floor((info.away % 3600) / 60)
	local awayText = if hours > 0 then hours .. "h " .. mins .. "m" else math.max(1, mins) .. "m"
	label({ Text = "You were away for " .. awayText, Size = UDim2.new(1, -40, 0, 36), Position = UDim2.fromOffset(20, 96),
		TextColor3 = Color3.fromHex("#cfe0ff"), ZIndex = 52, StrokeThickness = 2, Parent = panel })
	local coin = new("Frame", { BackgroundColor3 = Color3.fromHex("#0f1a36"), BackgroundTransparency = 0.2,
		Position = UDim2.fromOffset(40, 146), Size = UDim2.new(1, -80, 0, 110), ZIndex = 52, Parent = panel },
		{ corner(22), stroke(Color3.fromHex("#ffd23f"), 3) })
	local amount = label({ Text = "+$0", Size = UDim2.new(1, -30, 1, -20), Position = UDim2.fromOffset(15, 10),
		TextColor3 = Color3.fromHex("#7dff4f"), ZIndex = 53, StrokeThickness = 4, Parent = coin })
	-- how much of the offline cap was used
	local bar = new("Frame", { BackgroundColor3 = Color3.fromHex("#0f1a36"), Position = UDim2.fromOffset(60, 276),
		Size = UDim2.new(1, -120, 0, 18), ZIndex = 52, Parent = panel }, { corner(9) })
	local fill = new("Frame", { BackgroundColor3 = Color3.fromHex("#7dff4f"), Size = UDim2.fromScale(0, 1), ZIndex = 53,
		Parent = bar }, { corner(9), gradient(Color3.fromHex("#b8ff6a"), Color3.fromHex("#16b83a"), 0) })
	local capH = math.floor((info.cap or 28800) / 3600)
	label({ Text = math.floor((info.rate or 0.25) * 100) .. "% of your income while offline  •  max " .. capH .. "h",
		Size = UDim2.new(1, -40, 0, 28), Position = UDim2.fromOffset(20, 300), TextColor3 = Color3.fromHex("#aebfe6"),
		ZIndex = 52, StrokeThickness = 2, Parent = panel })
	local collect = new("TextButton", { Name = "Collect", Text = "", AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 344), Size = UDim2.fromOffset(300, 74), ZIndex = 52, AutoButtonColor = false,
		BackgroundColor3 = Color3.new(1, 1, 1), Parent = panel },
		{ corner(18), stroke(INK, 4), new("UIGradient", { Name = "Gradient", Rotation = 90 }) })
	self.ctx.setPreset(collect, "green")
	label({ Name = "Label", Text = "COLLECT", Size = UDim2.fromScale(1, 0.8), Position = UDim2.fromScale(0, 0.1),
		ZIndex = 53, StrokeThickness = 3, Parent = collect })
	vfx:BindButton(collect)
	vfx:Sound("Milestone")
	-- count up with coin ticks
	local value = new("NumberValue", { Value = 0 })
	value.Changed:Connect(function(v)
		amount.Text = "+" .. Format.money(math.floor(v))
	end)
	task.delay(0.35, function()
		tween(value, 1.4, { Value = info.amount }, Enum.EasingStyle.Quart)
		tween(fill, 1.4, { Size = UDim2.fromScale(math.clamp((info.paid or 0) / math.max(info.cap or 1, 1), 0.03, 1), 1) },
			Enum.EasingStyle.Quart)
		for i = 1, 12 do
			task.delay(i * 0.1, function()
				vfx:Sound("Coin", 0.9 + i * 0.05)
			end)
		end
	end)
	local spin = RunService.RenderStepped:Connect(function(dt)
		rays.Rotation += dt * 20
	end)
	local closed = false
	local function close()
		if closed then
			return
		end
		closed = true
		value.Value = info.amount
		local p = collect.AbsolutePosition + collect.AbsoluteSize / 2
		vfx:Confetti(p, Color3.fromHex("#ffd23f"), vfx:Q(50), false)
		vfx:UIBurst(p, Color3.fromHex("#7dff4f"), vfx:Q(30), 220)
		vfx:Purchase("Purchase")
		if self.ctx.uiFX and self.ctx.uiFX.CashGleam then
			self.ctx.uiFX:CashGleam()
		end
		tween(scale, 0.25, { Scale = 0.1 }, Enum.EasingStyle.Back, Enum.EasingDirection.In)
		tween(holder, 0.3, { BackgroundTransparency = 1 })
		tween(rays, 0.3, { ImageTransparency = 1 })
		task.delay(0.32, function()
			spin:Disconnect()
			value:Destroy()
			holder:Destroy()
		end)
	end
	collect.Activated:Connect(close)
end

-- ------------------------------------------------------------------ second floor (build panel)
function Systems:BuildFloorButton()
	local panel = self.root:WaitForChild("BuildPanel")
	local rotate = panel:WaitForChild("RotateButton")
	local b = freshClone(rotate)
	b.Name = "FloorButton"
	b.Position = UDim2.new(1, -560, 0, 12)
	b.Size = UDim2.fromOffset(158, 50)
	b.Parent = panel
	self.floorButton = b
	self.vfx:BindButton(b)
	b.Activated:Connect(function()
		self:FloorClicked()
	end)
	local hint = panel:FindFirstChild("Hint")
	if hint and hint:IsA("TextLabel") then
		hint.Text = "Click to place  •  R rotate  •  F floor  •  Right-click cancel"
	end
end

function Systems:FloorClicked()
	local snap = self.snap
	if not snap then
		return
	end
	if Stats.floors(snap.Data) < 2 then
		if os.clock() - self.floorConfirm > 3 then
			self.floorConfirm = os.clock()
			self:RefreshFloor()
			return
		end
		self.floorConfirm = 0
		local ok, msg = self.ctx.request("BuyFloor")
		self.ctx.toast(msg or (if ok then "2nd floor unlocked!" else "Not enough cash!"),
			if ok then "#9dff7a" else "#ff8a96")
		if ok then
			self:SetBuildFloor(1)
		end
		self:RefreshFloor()
		return
	end
	self:SetBuildFloor(1 - self.buildFloor)
end

function Systems:SetBuildFloor(f: number)
	if not self.snap or Stats.floors(self.snap.Data) < 2 then
		f = 0
	end
	if f ~= self.buildFloor then
		self.vfx:Sound("Whoosh", if f == 1 then 1.2 else 0.9, 0.3)
	end
	self.buildFloor = f
	self:RefreshFloor()
	self:UpdateFloorView()
	if self.OnFloorChanged then
		self.OnFloorChanged(f)
	end
end

function Systems:RefreshFloor()
	local b = self.floorButton
	local snap = self.snap
	if not b or not snap then
		return
	end
	if Stats.floors(snap.Data) < 2 then
		local price = Format.money(GameData.Config.SecondFloorPrice)
		if os.clock() - self.floorConfirm <= 3 then
			self.ctx.setPreset(b, "green")
			self.ctx.setText(b, "Buy " .. price .. "?")
		else
			self.ctx.setPreset(b, "yellow")
			self.ctx.setText(b, "🔒 2nd Floor")
		end
	else
		self.ctx.setPreset(b, if self.buildFloor == 1 then "purple" else "blue")
		self.ctx.setText(b, if self.buildFloor == 1 then "Floor 2 ▲" else "Floor 1 ▼")
	end
end

function Systems:SetSnap(snap)
	self.snap = snap
	if snap and Stats.floors(snap.Data) < 2 and self.buildFloor ~= 0 then
		self.buildFloor = 0
	end
	self:RefreshFloor()
	if self.window and self.window.Visible then
		self:Refresh()
	end
	if self.buildOpen then
		self:UpdateFloorView()
	end
end

function Systems:SetBuildOpen(on: boolean)
	self.buildOpen = on
	if not on then
		self.buildFloor = 0
		self:RefreshFloor()
	end
	self:UpdateFloorView()
end

local function myPlot(): Model?
	local map = Workspace:FindFirstChild("Map")
	local plots = map and map:FindFirstChild("Plots")
	if not plots then
		return nil
	end
	for _, plot in plots:GetChildren() do
		if plot:GetAttribute("OwnerId") == Players.LocalPlayer.UserId then
			return plot :: Model
		end
	end
	return nil
end

-- while building on floor 1 the second floor turns see-through; on floor 2 a glowing grid
-- floats at floor height over the unlocked cells
function Systems:UpdateFloorView()
	local plot = myPlot()
	local f2 = self.buildOpen and self.buildFloor == 1
	local ghostUpper = self.buildOpen and self.buildFloor == 0
	if plot then
		local track = plot:FindFirstChild("Track")
		if track then
			for _, m in track:GetChildren() do
				if m:GetAttribute("Floor") == 1 then
					for _, p in m:GetDescendants() do
						if p:IsA("BasePart") then
							p.LocalTransparencyModifier = if ghostUpper then 0.72 else 0
						end
					end
				end
			end
		end
		local pillars = plot:FindFirstChild("Pillars")
		if pillars then
			for _, p in pillars:GetDescendants() do
				if p:IsA("BasePart") then
					p.LocalTransparencyModifier = if ghostUpper then 0.6 else 0
				end
			end
		end
	end
	local size = if self.snap then Stats.gridSize(self.snap.Data) else 0
	if not f2 or not plot then
		if self.grid then
			self.grid:Destroy()
			self.grid = nil
		end
		return
	end
	if self.grid and self.grid:GetAttribute("Size") == size and self.grid:GetAttribute("Plot") == plot.Name then
		return
	end
	if self.grid then
		self.grid:Destroy()
	end
	local origin = (plot:FindFirstChild("GridOrigin") :: BasePart).CFrame
	local cell = Stats.Config.Cell
	local y = PAD_Y + Stats.FLOOR_H
	local g = new("Folder", { Name = "Floor2Grid" })
	g:SetAttribute("Size", size)
	g:SetAttribute("Plot", plot.Name)
	local half = size * cell / 2
	local function part(sz: Vector3, cf: CFrame, color: Color3, transp: number, neon: boolean)
		return new("Part", { Anchored = true, CanCollide = false, CanQuery = false, CanTouch = false, CastShadow = false,
			Size = sz, CFrame = cf, Color = color, Transparency = transp,
			Material = if neon then Enum.Material.Neon else Enum.Material.SmoothPlastic, Parent = g })
	end
	part(Vector3.new(size * cell, 0.1, size * cell), origin * CFrame.new(0, y - 0.1, 0), Color3.fromHex("#6fd0ff"), 0.86, false)
	for i = 0, size do
		local off = -half + i * cell
		part(Vector3.new(size * cell, 0.06, 0.18), origin * CFrame.new(0, y - 0.02, off), Color3.fromHex("#9fe8ff"), 0.45, true)
		part(Vector3.new(0.18, 0.06, size * cell), origin * CFrame.new(off, y - 0.02, 0), Color3.fromHex("#9fe8ff"), 0.45, true)
	end
	g.Parent = Workspace
	self.grid = g
	-- fade in
	for _, p in g:GetChildren() do
		local target = p.Transparency
		p.Transparency = 1
		tween(p, 0.35, { Transparency = target })
	end
end

-- ------------------------------------------------------------------ construction animations
local function serverNow(): number
	return Workspace:GetServerTimeNow()
end

local function fresh(inst: Instance): boolean
	local born = inst:GetAttribute("Born")
	return type(born) == "number" and born > 0 and serverNow() - born < 2.5
end

-- a part grows up from its bottom face (or out along its long axis for beams)
local function grow(p: BasePart, dur: number, delay: number, axis: string?)
	local size, cf = p.Size, p.CFrame
	local children = {}
	for _, c in p:GetChildren() do
		if c:IsA("BasePart") then
			table.insert(children, c)
			c.LocalTransparencyModifier = 1
		end
	end
	if axis == "Y" then
		p.Size = Vector3.new(size.X, 0.05, size.Z)
		p.CFrame = cf * CFrame.new(0, -size.Y / 2, 0)
	else
		local along = if size.X > size.Z then "X" else "Z"
		p.Size = if along == "X" then Vector3.new(0.05, size.Y, size.Z) else Vector3.new(size.X, size.Y, 0.05)
	end
	p.LocalTransparencyModifier = 1
	task.delay(delay, function()
		if not p.Parent then
			return
		end
		p.LocalTransparencyModifier = 0
		tween(p, dur, { Size = size, CFrame = cf }, Enum.EasingStyle.Back)
		task.delay(dur * 0.85, function()
			for _, c in children do
				if c.Parent then
					c.LocalTransparencyModifier = 0
				end
			end
		end)
	end)
end

function Systems:HookConstruction()
	local map = Workspace:WaitForChild("Map")
	local plots = map:WaitForChild("Plots")
	local function onPillar(p: Instance)
		if not p:IsA("BasePart") or not fresh(p) then
			return
		end
		local kind = p:GetAttribute("Kind")
		if kind == "P" then
			local base = p.Position - Vector3.new(0, p.Size.Y / 2, 0)
			grow(p, 0.45, math.random() * 0.12, "Y")
			self.vfx:WorldBurst(base + Vector3.new(0, 0.3, 0), Color3.fromHex("#d9cbb0"), self.vfx:Q(8), "Build")
			task.delay(0.45, function()
				if p.Parent then
					self.vfx:WorldBurst(p.Position + Vector3.new(0, p.Size.Y / 2, 0), Color3.fromHex("#ffd23f"),
						self.vfx:Q(10), "Spark")
				end
			end)
		else
			grow(p, 0.35, 0.3 + math.random() * 0.1)
		end
	end
	local function onFrame(frame: Instance)
		if frame.Name ~= "FloorFrame" or not fresh(frame) then
			return
		end
		task.defer(function()
			self:PlayFrameBuild(frame :: Model)
		end)
	end
	local function hookPlot(plot: Instance)
		local function hookPillars(folder: Instance)
			folder.ChildAdded:Connect(function(c)
				task.defer(onPillar, c)
			end)
		end
		local pf = plot:FindFirstChild("Pillars")
		if pf then
			hookPillars(pf)
		end
		plot.ChildAdded:Connect(function(c)
			if c.Name == "Pillars" then
				hookPillars(c)
				for _, p in c:GetChildren() do
					task.defer(onPillar, p)
				end
			elseif c.Name == "FloorFrame" then
				onFrame(c)
			end
		end)
	end
	for _, plot in plots:GetChildren() do
		hookPlot(plot)
	end
	plots.ChildAdded:Connect(hookPlot)
end

-- towers rise one after another, girders slide between them, beacons light up
function Systems:PlayFrameBuild(frame: Model)
	local vfx = self.vfx
	local mine = frame.Parent and frame.Parent:GetAttribute("OwnerId") == Players.LocalPlayer.UserId
	local towers, girders = {}, {}
	for _, c in frame:GetChildren() do
		if c.Name:match("^Tower") then
			table.insert(towers, c)
		elseif c.Name:match("^Girder") then
			table.insert(girders, c)
		end
	end
	table.sort(towers, function(a, b)
		return (a:GetAttribute("Order") or 0) < (b:GetAttribute("Order") or 0)
	end)
	table.sort(girders, function(a, b)
		return (a:GetAttribute("Order") or 0) < (b:GetAttribute("Order") or 0)
	end)
	-- hide everything first
	local saved = {}
	for _, p in frame:GetDescendants() do
		if p:IsA("BasePart") then
			saved[p] = { p.Size, p.CFrame }
			p.LocalTransparencyModifier = 1
		end
	end
	if mine then
		vfx:Banner("BUILDING 2ND FLOOR...", Color3.fromHex("#3bb8ff"), 0.7, UDim2.fromScale(0.5, 0.22), 1.6)
		vfx:Sound("Unlock", 0.8)
	end
	for i, tower in towers do
		task.delay((i - 1) * 0.42, function()
			for _, p in tower:GetChildren() do
				if p:IsA("BasePart") and saved[p] then
					local size, cf = saved[p][1], saved[p][2]
					if p.Name == "Column" then
						p.Size = Vector3.new(size.X, 0.1, size.Z)
						p.CFrame = cf * CFrame.new(0, -size.Y / 2, 0)
						p.LocalTransparencyModifier = 0
						tween(p, 0.7, { Size = size, CFrame = cf }, Enum.EasingStyle.Back)
						local base = cf.Position - Vector3.new(0, size.Y / 2, 0)
						vfx:WorldBurst(base + Vector3.new(0, 0.5, 0), Color3.fromHex("#d9cbb0"), vfx:Q(22), "Build")
						vfx:Sound("Place", 0.7, 0.45)
					else
						task.delay(0.6, function()
							p.LocalTransparencyModifier = 0
							local s0 = size * 0.2
							p.Size = s0
							tween(p, 0.35, { Size = size }, Enum.EasingStyle.Back)
							if p.Name == "Beacon" then
								vfx:WorldBurst(cf.Position, p.Color, vfx:Q(18), "Spark")
								vfx:Sound("Tick", 1.4, 0.4)
							end
						end)
					end
				end
			end
			if mine then
				vfx:CameraPunch(0.25, 0.2)
			end
		end)
	end
	local start = #towers * 0.42 + 0.5
	for i, girder in girders do
		task.delay(start + (i - 1) * 0.28, function()
			for _, p in girder:GetChildren() do
				if p:IsA("BasePart") and saved[p] then
					local size, cf = saved[p][1], saved[p][2]
					local alongX = size.X > size.Z
					p.Size = if alongX then Vector3.new(0.1, size.Y, size.Z) else Vector3.new(size.X, size.Y, 0.1)
					p.LocalTransparencyModifier = 0
					tween(p, 0.55, { Size = size }, Enum.EasingStyle.Quart)
					if p.Name == "Beam" then
						vfx:WorldBurst(cf.Position, Color3.fromHex("#ffd23f"), vfx:Q(16), "Spark")
						vfx:Sound("Whoosh", 0.8 + i * 0.1, 0.35)
					end
				end
			end
		end)
	end
	-- finale: a light sheet sweeps across floor height, fireworks from every tower
	task.delay(start + #girders * 0.28 + 0.4, function()
		local plot = frame.Parent
		local origin = plot and plot:FindFirstChild("GridOrigin")
		if origin and origin:IsA("BasePart") then
			local size = Stats.Config.MaxGrid * Stats.Config.Cell
			local sheet = new("Part", { Anchored = true, CanCollide = false, CanQuery = false, CanTouch = false,
				CastShadow = false, Material = Enum.Material.Neon, Color = Color3.fromHex("#7fe0ff"), Transparency = 0.35,
				Size = Vector3.new(size, 0.2, 0.6), CFrame = origin.CFrame * CFrame.new(0, PAD_Y + Stats.FLOOR_H, -size / 2),
				Parent = Workspace })
			tween(sheet, 0.9, { CFrame = origin.CFrame * CFrame.new(0, PAD_Y + Stats.FLOOR_H, size / 2),
				Transparency = 0.9 }, Enum.EasingStyle.Sine)
			task.delay(0.95, function()
				sheet:Destroy()
			end)
		end
		for _, tower in towers do
			local beacon = tower:FindFirstChild("Beacon")
			if beacon and beacon:IsA("BasePart") and self.worldFX and self.worldFX.Fireworks then
				self.worldFX:Fireworks(beacon.Position + Vector3.new(0, 2, 0),
					{ beacon.Color, Color3.new(1, 1, 1), Color3.fromHex("#ffd23f") }, 3)
			end
		end
		if mine then
			vfx:Banner("2ND FLOOR UNLOCKED!", Color3.fromHex("#ffd23f"), 0.85, UDim2.fromScale(0.5, 0.22), 1.8, true)
			vfx:Sound("Milestone")
			vfx:ScreenFlash(Color3.fromHex("#bfefff"), 0.6)
		end
	end)
end

return Systems

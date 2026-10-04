-- Living world (client only, presentation only): spinning golden die, drifting clouds, bobbing
-- sky isles, seagulls, butterflies, animated sea, waving flags, falling leaves, lamp lights,
-- pulsing track glow, portal swirls and per-car effects (exhaust, flames, sparks, landing dust).
-- Everything is distance-culled and thinned out on the "Low" effect setting.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local GameData = require(ReplicatedStorage.Shared.GameData)
local Stats = require(ReplicatedStorage.Shared.Stats)
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local FX = GameData.FX or {}
local TEX = {
	Star = FX.star or "rbxasset://textures/particles/sparkles_main.dds",
	Leaf = FX.leaf or "rbxasset://textures/particles/sparkles_main.dds",
	Streak = FX.streak or "rbxasset://textures/particles/sparkles_main.dds",
	Butterfly = FX.butterfly,
	Water = FX.water,
	Smoke = "rbxasset://textures/particles/smoke_main.dds",
	Fire = "rbxasset://textures/particles/fire_main.dds",
}
local TIER_COLOR = {
	Common = Color3.fromRGB(220, 230, 240),
	Rare = Color3.fromRGB(66, 197, 255),
	Epic = Color3.fromRGB(198, 83, 255),
	Legendary = Color3.fromRGB(255, 204, 44),
	Mythical = Color3.fromRGB(255, 60, 126),
	Secret = Color3.fromRGB(255, 255, 255),
}
local RANK = { Common = 1, Rare = 2, Epic = 3, Legendary = 4, Mythical = 5, Secret = 6 }

local WorldFX = {}
WorldFX.__index = WorldFX

local function seq(a, b)
	return NumberSequence.new(a, b)
end

local function anchor(parent: Instance, cf: CFrame, size: Vector3?): Part
	local p = Instance.new("Part")
	p.Name = "FXAnchor"
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Transparency = 1
	p.Size = size or Vector3.one
	p.CFrame = cf
	p.Parent = parent
	return p
end

local function emitter(parent: Instance, props): ParticleEmitter
	local e = Instance.new("ParticleEmitter")
	for k, v in props do
		(e :: any)[k] = v
	end
	e.Parent = parent
	return e
end

function WorldFX.new(gui: ScreenGui)
	local self = setmetatable({
		Gui = gui,
		Folder = Instance.new("Folder"),
		Connections = {},
		Spinners = {},
		Bobbers = {},
		Flags = {},
		Birds = {},
		Butterflies = {},
		Emitters = {},
		Glows = {},
		Cars = {},
		Clouds = {},
		Textures = {},
		T = 0,
	}, WorldFX)
	self.Folder.Name = "LocalWorldFX"
	self.Folder.Parent = workspace
	task.spawn(function()
		local map = workspace:WaitForChild("Map", 30)
		if map then
			self:Setup(map)
		end
	end)
	table.insert(self.Connections, RunService.Heartbeat:Connect(function(dt)
		self:Step(dt)
	end))
	gui.Destroying:Connect(function()
		self:Destroy()
	end)
	return self
end

function WorldFX:Low(): boolean
	return self.Gui:GetAttribute("VFXQuality") == "Low"
end

function WorldFX:Track(e: ParticleEmitter, pos: Vector3, range: number?)
	table.insert(self.Emitters, { e = e, pos = pos, range = range or 180, rate = e.Rate })
end

-- ------------------------------------------------------------------ setup
function WorldFX:Setup(map: Instance)
	local hub = map:WaitForChild("Hub", 10)
	-- golden die: spins, bobs, sparkles and every few seconds "rolls"
	local die = hub and hub:FindFirstChild("Landmark") and hub.Landmark:FindFirstChild("Die")
	if die and die:IsA("Model") then
		local cf = die:GetPivot()
		local a = anchor(self.Folder, cf, Vector3.new(10, 10, 10))
		local light = Instance.new("PointLight")
		light.Color = Color3.fromRGB(255, 214, 90)
		light.Range = 26
		light.Brightness = 1.4
		light.Shadows = false
		light.Parent = a
		local sparkle = emitter(a, {
			Texture = TEX.Star, Rate = 6, Lifetime = NumberRange.new(1, 1.8), Speed = NumberRange.new(1, 3),
			SpreadAngle = Vector2.new(180, 180), Size = seq(0.9, 0), LightEmission = 1,
			Color = ColorSequence.new(Color3.fromRGB(255, 230, 120), Color3.new(1, 1, 1)),
			Transparency = seq(0.1, 1), Shape = Enum.ParticleEmitterShape.Sphere,
			ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface, ZOffset = 1,
		})
		self:Track(sparkle, cf.Position, 260)
		self.Die = { model = die, base = cf, anchor = a, spin = 0, roll = nil, next = 6, sparkle = sparkle }
		-- shimmering ring of light on the fountain water
		local ring = anchor(self.Folder, CFrame.new(cf.Position.X, cf.Position.Y - 15, cf.Position.Z),
			Vector3.new(26, 0.2, 26))
		self:Track(emitter(ring, {
			Texture = TEX.Star, Rate = 10, Lifetime = NumberRange.new(0.6, 1.1), Speed = NumberRange.new(0.5, 2),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.6, 0), LightEmission = 1,
			Color = ColorSequence.new(Color3.fromRGB(150, 235, 255)), Transparency = seq(0.2, 1),
		}), ring.Position, 200)
	end
	-- magic dust floating over the plaza
	if hub then
		local plaza = anchor(self.Folder, CFrame.new(0, 104, 0), Vector3.new(70, 1, 70))
		self:Track(emitter(plaza, {
			Texture = TEX.Star, Rate = 5, Lifetime = NumberRange.new(4, 7), Speed = NumberRange.new(0.6, 1.4),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.45, 0), LightEmission = 0.8,
			Color = ColorSequence.new(Color3.fromRGB(255, 240, 170), Color3.fromRGB(160, 230, 255)),
			Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.2, 0.2),
				NumberSequenceKeypoint.new(1, 1) }), RotSpeed = NumberRange.new(-60, 60),
		}), plaza.Position, 260)
	end
	-- lamps get a warm light
	for _, d in map:GetDescendants() do
		if d:IsA("MeshPart") and d.Name == "Glow" and d.Parent and d.Parent.Name == "Lamp" then
			local l = Instance.new("PointLight")
			l.Color = Color3.fromRGB(255, 225, 160)
			l.Range = 16
			l.Brightness = 0.9
			l.Shadows = false
			l.Parent = d
		end
	end
	-- leaves drifting from trees
	for _, m in map:GetDescendants() do
		if m:IsA("Model") and (m.Name == "TreeRound" or m.Name == "TreePalm") then
			local cf, size = m:GetBoundingBox()
			local a = anchor(self.Folder, cf * CFrame.new(0, size.Y * 0.2, 0), Vector3.new(size.X * 0.7, 1, size.Z * 0.7))
			self:Track(emitter(a, {
				Texture = TEX.Leaf, Rate = 0.6, Lifetime = NumberRange.new(4, 6), Speed = NumberRange.new(0.5, 1),
				EmissionDirection = Enum.NormalId.Bottom, Acceleration = Vector3.new(1.2, -0.6, 0.6),
				Size = seq(0.55, 0.45), RotSpeed = NumberRange.new(-90, 90), Rotation = NumberRange.new(0, 360),
				Color = ColorSequence.new(Color3.fromRGB(110, 210, 80), Color3.fromRGB(70, 170, 60)),
				Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.1, 0),
					NumberSequenceKeypoint.new(0.85, 0), NumberSequenceKeypoint.new(1, 1) }),
				Drag = 0.6,
			}), a.Position, 140)
		end
	end
	-- plot flags wave
	for _, f in map:GetDescendants() do
		if f:IsA("BasePart") and f.Name == "Flag" then
			table.insert(self.Flags, { part = f, base = f.CFrame, phase = math.random() * 6 })
		end
	end
	-- clouds drift, sky isles bob
	local clouds = map:FindFirstChild("Clouds")
	if clouds then
		for _, c in clouds:GetChildren() do
			if c:IsA("BasePart") then
				table.insert(self.Clouds, { part = c, speed = 2 + math.random() * 3 })
			end
		end
	end
	local isles = map:FindFirstChild("FloatingIsles")
	if isles then
		for _, p in isles:GetChildren() do
			if p:IsA("BasePart") then
				table.insert(self.Bobbers, { part = p, base = p.CFrame, phase = math.random() * 6, amp = 2.2, spin = 0.03 })
			end
		end
	end
	-- animated sea: two layers of moving wave highlights
	if TEX.Water then
		for _, o in map:GetChildren() do
			if o:IsA("BasePart") and o.Name == "Ocean" then
				for k = 1, 2 do
					local t = Instance.new("Texture")
					t.Face = Enum.NormalId.Top
					t.Texture = TEX.Water
					t.StudsPerTileU = k == 1 and 90 or 140
					t.StudsPerTileV = k == 1 and 90 or 140
					t.Transparency = k == 1 and 0.35 or 0.6
					t.Color3 = Color3.fromRGB(230, 250, 255)
					t.Parent = o
					table.insert(self.Textures, { tex = t, du = k == 1 and 2.4 or -1.6, dv = k == 1 and 1.2 or 2 })
				end
			end
		end
	end
	self:SpawnBirds()
	self:SpawnButterflies(hub)
	if hub then
		self:StallHolograms(hub)
		self:FountainJets(hub)
	end
	self:Waterfalls(map)
	self:ShoreFoam(map)
	self:Character()
	-- track tiles and cars on every plot
	local plots = map:WaitForChild("Plots", 10)
	if plots then
		for _, plot in plots:GetChildren() do
			local track = plot:WaitForChild("Track", 5)
			if track then
				for _, m in track:GetChildren() do
					self:Tile(m)
				end
				table.insert(self.Connections, track.ChildAdded:Connect(function(m)
					task.delay(0.1, function()
						self:Tile(m)
					end)
				end))
			end
			local pad = plot:FindFirstChild("Pad")
			if pad then
				local function border()
					if plot:GetAttribute("OwnerId") == Players.LocalPlayer.UserId then
						task.defer(self.PadBorder, self, plot)
					end
				end
				table.insert(self.Connections, pad.ChildAdded:Connect(border))
				table.insert(self.Connections, plot:GetAttributeChangedSignal("OwnerId"):Connect(border))
				border()
			end
			table.insert(self.Connections, plot.ChildAdded:Connect(function(o)
				if o.Name == "Car" then
					task.defer(function()
						self:Car(o)
					end)
				end
			end))
			local car = plot:FindFirstChild("Car")
			if car then
				self:Car(car)
			end
		end
	end
end


-- ------------------------------------------------------------------ hub extras
local function glowRing(parent: Instance, cf: CFrame, radius: number, color: Color3): Part
	local r = Instance.new("Part")
	r.Name = "HoloRing"
	r.Anchored = true
	r.CanCollide = false
	r.CanQuery = false
	r.CanTouch = false
	r.CastShadow = false
	r.Shape = Enum.PartType.Cylinder
	r.Material = Enum.Material.Neon
	r.Color = color
	r.Transparency = 0.45
	r.Size = Vector3.new(0.2, radius * 2, radius * 2)
	r.CFrame = cf * CFrame.Angles(0, 0, math.pi / 2)
	r.Parent = parent
	return r
end

-- spinning hologram of what each stall sells, floating above it
function WorldFX:StallHolograms(hub: Instance)
	local assets = ReplicatedStorage:WaitForChild("Assets")
	local colors = { Cars = Color3.fromRGB(60, 150, 255), Styles = Color3.fromRGB(255, 110, 180),
		Potions = Color3.fromRGB(180, 90, 255), Dice = Color3.fromRGB(255, 190, 40) }
	for _, shop in hub:GetChildren() do
		local key = shop:GetAttribute("Shop")
		if not key then
			continue
		end
		local cf, size = shop:GetBoundingBox()
		local top = CFrame.new(cf.Position + Vector3.new(0, size.Y / 2 + 5.5, 0))
		local color = colors[key] or Color3.new(1, 1, 1)
		local holo: Instance? = nil
		if key == "Cars" then
			local car = assets.Cars:FindFirstChild("Sports")
			if car then
				holo = car:Clone()
				;(holo :: Model):ScaleTo(2)
			end
		elseif key == "Styles" then
			local isl = assets:FindFirstChild("IslandPreview")
			if isl then
				holo = isl:Clone()
				;(holo :: Model):ScaleTo(0.32)
			end
		else
			local a = anchor(self.Folder, top, Vector3.one)
			local bb = Instance.new("BillboardGui")
			bb.Size = UDim2.fromScale(7, 7)
			bb.LightInfluence = 0
			bb.MaxDistance = 220
			bb.Parent = a
			local img = Instance.new("ImageLabel")
			img.BackgroundTransparency = 1
			img.Size = UDim2.fromScale(1, 1)
			local list = key == "Dice" and GameData.Dice or GameData.Potions
			img.Image = list[#list].image or list[1].image or ""
			img.Parent = bb
			holo = a
			table.insert(self.Spinners, { kind = "billboard", obj = a, base = top, img = img, list = list, i = #list,
				next = 3, phase = math.random() * 6 })
		end
		if holo and holo:IsA("Model") then
			for _, p in holo:GetDescendants() do
				if p:IsA("BasePart") then
					p.Anchored = true
					p.CanCollide = false
					p.CanQuery = false
					p.CastShadow = false
				end
			end
			holo:PivotTo(top)
			holo.Parent = self.Folder
			table.insert(self.Spinners, { kind = "model", obj = holo, base = top, phase = math.random() * 6 })
		end
		local ring = glowRing(self.Folder, top * CFrame.new(0, -3.2, 0), 3.4, color)
		table.insert(self.Spinners, { kind = "ring", obj = ring, base = ring.CFrame, phase = math.random() * 6 })
		local light = Instance.new("PointLight")
		light.Color = color
		light.Range = 14
		light.Brightness = 1.2
		light.Parent = ring
		local sp = anchor(self.Folder, top * CFrame.new(0, -3, 0), Vector3.new(6, 0.2, 6))
		self:Track(emitter(sp, {
			Texture = TEX.Star, Rate = 6, Lifetime = NumberRange.new(0.8, 1.4), Speed = NumberRange.new(2, 4),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.45, 0), LightEmission = 1,
			Color = ColorSequence.new(color, Color3.new(1, 1, 1)), Transparency = seq(0.1, 1),
		}), sp.Position, 200)
		-- the stall lights up when you walk up to it
		local prompt = shop:FindFirstChild("PromptPart") and shop.PromptPart:FindFirstChildOfClass("ProximityPrompt")
		if prompt then
			local h = Instance.new("Highlight")
			h.FillTransparency = 1
			h.OutlineColor = color
			h.OutlineTransparency = 1
			h.DepthMode = Enum.HighlightDepthMode.Occluded
			h.Adornee = shop
			h.Parent = self.Folder
			table.insert(self.Connections, prompt.PromptShown:Connect(function()
				TweenService:Create(h, TweenInfo.new(0.25), { OutlineTransparency = 0 }):Play()
				self:Burst(top.Position - Vector3.new(0, 3, 0), color, 18)
			end))
			table.insert(self.Connections, prompt.PromptHidden:Connect(function()
				TweenService:Create(h, TweenInfo.new(0.3), { OutlineTransparency = 1 }):Play()
			end))
		end
	end
end

function WorldFX:FountainJets(hub: Instance)
	local lm = hub:FindFirstChild("Landmark")
	if not lm then
		return
	end
	local c = lm:GetBoundingBox().Position
	local base = Vector3.new(c.X, 100.3, c.Z)
	for k = 0, 5 do
		local a = k / 6 * math.pi * 2
		local p = base + Vector3.new(math.cos(a) * 9.7, 3.2, math.sin(a) * 9.7)
		local an = anchor(self.Folder, CFrame.lookAt(p, base + Vector3.new(0, 8, 0)), Vector3.new(0.4, 0.4, 0.4))
		self:Track(emitter(an, {
			Texture = TEX.Star, Rate = 26, Lifetime = NumberRange.new(0.7, 0.9), Speed = NumberRange.new(9, 10),
			EmissionDirection = Enum.NormalId.Front, SpreadAngle = Vector2.new(4, 4),
			Acceleration = Vector3.new(0, -28, 0), Size = seq(0.45, 0.25), LightEmission = 0.4,
			Color = ColorSequence.new(Color3.fromRGB(170, 235, 255), Color3.new(1, 1, 1)), Transparency = seq(0.15, 0.8),
		}), p, 220)
	end
end

function WorldFX:Waterfalls(map: Instance)
	local isles = map:FindFirstChild("FloatingIsles")
	if not isles then
		return
	end
	for i, p in isles:GetChildren() do
		if p:IsA("BasePart") and i % 2 == 1 then
			local an = anchor(self.Folder, p.CFrame * CFrame.new(p.Size.X * 0.32, -p.Size.Y * 0.05, 0), Vector3.new(4, 0.5, 2))
			self:Track(emitter(an, {
				Texture = TEX.Smoke, Rate = 30, Lifetime = NumberRange.new(2.4, 3), Speed = NumberRange.new(2, 4),
				EmissionDirection = Enum.NormalId.Bottom, Acceleration = Vector3.new(0, -14, 0),
				Size = seq(1.2, 3.4), Color = ColorSequence.new(Color3.fromRGB(170, 225, 255), Color3.new(1, 1, 1)),
				Transparency = seq(0.35, 1),
			}), an.Position, 700)
		end
	end
end

function WorldFX:ShoreFoam(map: Instance)
	local spots = {}
	for k = 1, 14 do
		local a = k / 14 * math.pi * 2
		table.insert(spots, CFrame.new(math.cos(a) * 104, 92.2, math.sin(a) * 104) * CFrame.Angles(0, -a, 0))
	end
	local plots = map:FindFirstChild("Plots")
	for _, plot in (plots and plots:GetChildren() or {}) do
		local pv = plot:FindFirstChild("Pivot")
		if pv then
			for _, off in { Vector3.new(118, 0, 0), Vector3.new(-118, 0, 0), Vector3.new(0, 0, 128), Vector3.new(0, 0, -128),
				Vector3.new(90, 0, 100), Vector3.new(-90, 0, 100), Vector3.new(90, 0, -100), Vector3.new(-90, 0, -100) } do
				local w = pv.CFrame * CFrame.new(off)
				table.insert(spots, CFrame.new(w.Position.X, 92.2, w.Position.Z))
			end
		end
	end
	for _, cf in spots do
		local an = anchor(self.Folder, cf, Vector3.new(26, 0.2, 26))
		self:Track(emitter(an, {
			Texture = TEX.Smoke, Rate = 2.5, Lifetime = NumberRange.new(2, 3), Speed = NumberRange.new(0.3, 0.8),
			EmissionDirection = Enum.NormalId.Top, Size = seq(1.4, 3), Orientation = Enum.ParticleOrientation.FacingCameraWorldUp,
			Color = ColorSequence.new(Color3.new(1, 1, 1)), Transparency = NumberSequence.new({
				NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.3, 0.45), NumberSequenceKeypoint.new(1, 1) }),
		}), an.Position, 260)
	end
end

-- ------------------------------------------------------------------ one-shot effects
function WorldFX:Burst(pos: Vector3, color: Color3, count: number)
	local a = anchor(self.Folder, CFrame.new(pos), Vector3.one)
	local e = emitter(a, {
		Texture = TEX.Star, Rate = 0, Lifetime = NumberRange.new(0.5, 0.9), Speed = NumberRange.new(6, 12),
		SpreadAngle = Vector2.new(180, 180), Size = seq(0.6, 0), LightEmission = 1, Drag = 3,
		Color = ColorSequence.new(color, Color3.new(1, 1, 1)), Transparency = seq(0, 1),
	})
	e:Emit(self:Low() and math.ceil(count / 2) or count)
	Debris:AddItem(a, 1.2)
end

-- rockets that whistle up and burst into coloured stars
function WorldFX:Fireworks(center: Vector3, colors: { Color3 }, count: number?)
	local n = self:Low() and 3 or (count or 7)
	for i = 1, n do
		task.delay((i - 1) * 0.22 + math.random() * 0.15, function()
			local start = center + Vector3.new(math.random(-30, 30), 0, math.random(-30, 30))
			local peak = start + Vector3.new(math.random(-8, 8), 45 + math.random(0, 25), math.random(-8, 8))
			local color = colors[(i - 1) % #colors + 1]
			local rocket = anchor(self.Folder, CFrame.new(start), Vector3.new(0.6, 0.6, 0.6))
			rocket.Transparency = 0
			rocket.Material = Enum.Material.Neon
			rocket.Color = color
			local a0, a1 = Instance.new("Attachment"), Instance.new("Attachment")
			a0.Position = Vector3.new(0, 0.3, 0)
			a1.Position = Vector3.new(0, -0.3, 0)
			a0.Parent, a1.Parent = rocket, rocket
			local tr = Instance.new("Trail")
			tr.Attachment0, tr.Attachment1 = a0, a1
			tr.Lifetime = 0.5
			tr.LightEmission = 1
			tr.Color = ColorSequence.new(color, Color3.new(1, 1, 1))
			tr.Transparency = seq(0, 1)
			tr.WidthScale = seq(1, 0)
			tr.Parent = rocket
			local tw = TweenService:Create(rocket, TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
				{ CFrame = CFrame.new(peak) })
			tw:Play()
			tw.Completed:Connect(function()
				rocket.Transparency = 1
				local e = emitter(rocket, {
					Texture = TEX.Star, Rate = 0, Lifetime = NumberRange.new(1, 1.6), Speed = NumberRange.new(18, 28),
					SpreadAngle = Vector2.new(180, 180), Size = seq(1.1, 0), LightEmission = 1, Drag = 2.5,
					Acceleration = Vector3.new(0, -9, 0), Color = ColorSequence.new(color, Color3.new(1, 1, 1)),
					Transparency = seq(0, 1),
				})
				e:Emit(70)
				local crackle = emitter(rocket, {
					Texture = TEX.Star, Rate = 0, Lifetime = NumberRange.new(0.2, 0.5), Speed = NumberRange.new(8, 14),
					SpreadAngle = Vector2.new(180, 180), Size = seq(0.4, 0), LightEmission = 1,
					Color = ColorSequence.new(Color3.new(1, 1, 1)), Transparency = seq(0, 1),
				})
				task.delay(0.6, function()
					crackle:Emit(40)
				end)
				local l = Instance.new("PointLight")
				l.Color = color
				l.Range = 60
				l.Brightness = 3
				l.Parent = rocket
				TweenService:Create(l, TweenInfo.new(1.2), { Brightness = 0 }):Play()
				Debris:AddItem(rocket, 2.2)
			end)
		end)
	end
end

-- shrink-and-spin ghost of a tile that was just removed
function WorldFX:RemoveGhost(model: Model)
	local copy = model:Clone()
	for _, p in copy:GetDescendants() do
		if p:IsA("BasePart") then
			p.Anchored = true
			p.CanCollide = false
			p.CanQuery = false
		elseif p:IsA("Highlight") then
			p:Destroy()
		end
	end
	copy.Parent = self.Folder
	local pivot = copy:GetPivot()
	local size = copy:GetScale()
	local v = Instance.new("NumberValue")
	v.Value = 0
	v.Changed:Connect(function(k)
		if copy.Parent then
			copy:ScaleTo(math.max(0.05, size * (1 - k)))
			copy:PivotTo(pivot * CFrame.new(0, k * 4, 0) * CFrame.Angles(0, k * 4, 0))
		end
	end)
	TweenService:Create(v, TweenInfo.new(0.4, Enum.EasingStyle.Back, Enum.EasingDirection.In), { Value = 1 }):Play()
	self:Burst(pivot.Position, Color3.fromRGB(255, 120, 140), 22)
	Debris:AddItem(copy, 0.45)
	Debris:AddItem(v, 0.5)
end

-- ------------------------------------------------------------------ own plot: glowing pad border
function WorldFX:PadBorder(plot: Instance)
	if self.Border then
		self.Border:Destroy()
	end
	local slab = plot:FindFirstChild("Pad") and plot.Pad:FindFirstChild("Slab") :: BasePart?
	if not slab then
		return
	end
	local color = Color3.fromHex(plot:GetAttribute("PlotColor") or "#3bd1ff")
	local holder = anchor(self.Folder, slab.CFrame * CFrame.new(0, slab.Size.Y / 2 + 0.25, 0), Vector3.one)
	holder.Name = "PadBorder"
	self.Border = holder
	local hx, hz = slab.Size.X / 2, slab.Size.Z / 2
	local corners = { Vector3.new(-hx, 0, -hz), Vector3.new(hx, 0, -hz), Vector3.new(hx, 0, hz), Vector3.new(-hx, 0, hz) }
	local atts = {}
	for i, c in corners do
		local a = Instance.new("Attachment")
		a.Position = c
		a.Axis = Vector3.new(0, 1, 0)
		a.SecondaryAxis = Vector3.new(1, 0, 0)
		a.Parent = holder
		atts[i] = a
	end
	for i = 1, 4 do
		local b = Instance.new("Beam")
		b.Attachment0 = atts[i]
		b.Attachment1 = atts[i % 4 + 1]
		b.Texture = TEX.Streak
		b.TextureMode = Enum.TextureMode.Static
		b.TextureLength = 6
		b.TextureSpeed = 1.2
		b.Width0, b.Width1 = 0.9, 0.9
		b.FaceCamera = true
		b.LightEmission = 1
		b.Color = ColorSequence.new(color, Color3.new(1, 1, 1))
		b.Transparency = seq(0.15, 0.15)
		b.Segments = 1
		b.Parent = holder
		local e = emitter(atts[i], {
			Texture = TEX.Star, Rate = 3, Lifetime = NumberRange.new(0.8, 1.2), Speed = NumberRange.new(2, 4),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.7, 0), LightEmission = 1,
			Color = ColorSequence.new(color), Transparency = seq(0, 1),
		})
		self:Track(e, holder.Position, 220)
	end
end

-- ------------------------------------------------------------------ build mode: animated route arrows
function WorldFX:ShowRoute(plot: Instance?, data, on: boolean)
	if self.Route then
		self.Route:Destroy()
		self.Route = nil
	end
	if not on or not plot or not data then
		return
	end
	local origin = plot:FindFirstChild("GridOrigin") :: BasePart?
	if not origin then
		return
	end
	local tiles = ReplicatedStorage.Assets.Tiles
	local folder = Instance.new("Folder")
	folder.Name = "Route"
	folder.Parent = self.Folder
	self.Route = folder
	local holder = anchor(folder, CFrame.identity, Vector3.one)
	local c = Stats.center()
	local cell = Stats.Config.Cell
	local points = {}
	for _, step in Stats.tracePath(data) do
		local cf = origin.CFrame * CFrame.new((step.x - c) * cell, 0.3, (step.z - c) * cell)
			* CFrame.Angles(0, -step.r * math.pi / 2, 0)
		local tile = tiles:FindFirstChild(step.id)
		local path = tile and tile:FindFirstChild("Path")
		if path then
			local wps = path:GetChildren()
			table.sort(wps, function(a, b)
				return tonumber(a.Name) < tonumber(b.Name)
			end)
			local n = #wps
			for k = 1, n, 2 do
				local w = wps[if step.forward then k else n - k + 1] :: BasePart
				table.insert(points, { cf = cf * w.CFrame * CFrame.new(0, 0.45, 0), jump = w:GetAttribute("Teleport") == true })
			end
		end
	end
	local prev = nil
	for i, p in points do
		if i > 600 then
			break
		end
		local a = Instance.new("Attachment")
		a.WorldCFrame = p.cf
		a.Parent = holder
		if prev and (prev.WorldPosition - a.WorldPosition).Magnitude < 8 then
			local b = Instance.new("Beam")
			b.Attachment0, b.Attachment1 = prev, a
			b.Texture = TEX.Streak
			b.TextureMode = Enum.TextureMode.Static
			b.TextureLength = 2.5
			b.TextureSpeed = 2.5
			b.Width0, b.Width1 = 0.8, 0.8
			b.FaceCamera = true
			b.LightEmission = 1
			b.Color = ColorSequence.new(Color3.fromRGB(110, 255, 200))
			b.Transparency = seq(0.2, 0.2)
			b.Parent = holder
		end
		prev = a
	end
end

-- ------------------------------------------------------------------ the player's character
function WorldFX:Character()
	local function setup(char: Model)
		local hrp = char:WaitForChild("HumanoidRootPart", 10) :: BasePart?
		local hum = char:WaitForChild("Humanoid", 10) :: Humanoid?
		if not hrp or not hum then
			return
		end
		local feet = Instance.new("Attachment")
		feet.Position = Vector3.new(0, -2.8, 0)
		feet.Parent = hrp
		local dust = emitter(feet, {
			Texture = TEX.Smoke, Rate = 0, Lifetime = NumberRange.new(0.35, 0.6), Speed = NumberRange.new(1, 2),
			SpreadAngle = Vector2.new(60, 60), EmissionDirection = Enum.NormalId.Top, Size = seq(0.5, 1.4),
			Color = ColorSequence.new(Color3.fromRGB(235, 230, 220)), Transparency = seq(0.55, 1), Drag = 2,
		})
		local splash = emitter(feet, {
			Texture = TEX.Star, Rate = 0, Lifetime = NumberRange.new(0.6, 1), Speed = NumberRange.new(10, 18),
			SpreadAngle = Vector2.new(35, 35), EmissionDirection = Enum.NormalId.Top, Acceleration = Vector3.new(0, -40, 0),
			Size = seq(0.7, 0.2), Color = ColorSequence.new(Color3.fromRGB(170, 230, 255), Color3.new(1, 1, 1)),
			Transparency = seq(0.1, 1),
		})
		local wasAbove = true
		table.insert(self.Connections, hum.StateChanged:Connect(function(_, new)
			if new == Enum.HumanoidStateType.Landed then
				dust:Emit(self:Low() and 4 or 12)
			end
		end))
		table.insert(self.Connections, RunService.Heartbeat:Connect(function()
			if not hrp.Parent then
				return
			end
			local running = hum.FloorMaterial ~= Enum.Material.Air and hrp.AssemblyLinearVelocity.Magnitude > 10
			dust.Rate = (running and not self:Low()) and 10 or 0
			local above = hrp.Position.Y > 93
			if wasAbove and not above then
				splash:Emit(40)
			end
			wasAbove = above
		end))
	end
	local plr = Players.LocalPlayer
	if plr.Character then
		task.spawn(setup, plr.Character)
	end
	table.insert(self.Connections, plr.CharacterAdded:Connect(setup))
end

-- ------------------------------------------------------------------ creatures
function WorldFX:SpawnBirds()
	for i = 1, 7 do
		local m = Instance.new("Model")
		m.Name = "Seagull"
		local function piece(size, color)
			local p = Instance.new("Part")
			p.Anchored = true
			p.CanCollide = false
			p.CanQuery = false
			p.CanTouch = false
			p.CastShadow = false
			p.Size = size
			p.Color = color
			p.Material = Enum.Material.SmoothPlastic
			p.Parent = m
			return p
		end
		local body = piece(Vector3.new(0.9, 0.8, 2.6), Color3.fromRGB(250, 250, 250))
		local beak = piece(Vector3.new(0.3, 0.3, 0.6), Color3.fromRGB(255, 180, 40))
		local wl = piece(Vector3.new(2.8, 0.15, 1.1), Color3.fromRGB(235, 240, 245))
		local wr = piece(Vector3.new(2.8, 0.15, 1.1), Color3.fromRGB(235, 240, 245))
		m.Parent = self.Folder
		table.insert(self.Birds, {
			body = body, beak = beak, wl = wl, wr = wr,
			center = Vector3.new(math.random(-500, 500), 0, math.random(-500, 500)),
			radius = math.random(60, 160), height = 130 + math.random(0, 50),
			speed = (0.12 + math.random() * 0.1) * (i % 2 == 0 and 1 or -1), phase = math.random() * 6,
		})
	end
end

function WorldFX:SpawnButterflies(hub: Instance?)
	if not hub or not TEX.Butterfly then
		return
	end
	local colors = { Color3.fromRGB(255, 120, 200), Color3.fromRGB(255, 220, 70), Color3.fromRGB(120, 200, 255),
		Color3.fromRGB(180, 130, 255), Color3.fromRGB(255, 160, 80) }
	for i = 1, 12 do
		local a = (i + 0.5) / 12 * math.pi * 2
		local home = Vector3.new(math.cos(a) * 48, 102.5, math.sin(a) * 48)
		local p = anchor(self.Folder, CFrame.new(home), Vector3.new(0.1, 0.1, 0.1))
		local bb = Instance.new("BillboardGui")
		bb.Size = UDim2.fromScale(1.4, 1.4)
		bb.LightInfluence = 0.6
		bb.MaxDistance = 140
		bb.Parent = p
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.Size = UDim2.fromScale(1, 1)
		img.AnchorPoint = Vector2.new(0.5, 0.5)
		img.Position = UDim2.fromScale(0.5, 0.5)
		img.Image = TEX.Butterfly
		img.ImageColor3 = colors[(i % #colors) + 1]
		img.Parent = bb
		table.insert(self.Butterflies, { part = p, img = img, home = home, phase = math.random() * 10 })
	end
end

-- ------------------------------------------------------------------ track tiles
function WorldFX:Tile(m: Instance)
	if not m:IsA("Model") or m:GetAttribute("WorldFX") then
		return
	end
	local id = m:GetAttribute("PieceId")
	local piece = id and Stats.Pieces[id]
	if not piece then
		return
	end
	m:SetAttribute("WorldFX", true)
	local rank = RANK[piece.tier] or 1
	local hit = m:FindFirstChild("Hitbox") :: BasePart?
	local base = hit and hit.CFrame or m:GetPivot()
	for _, p in m:GetDescendants() do
		if p:IsA("MeshPart") and p.Material == Enum.Material.Neon then
			table.insert(self.Glows, { part = p, color = p.Color, speed = 1 + rank * 0.5, phase = math.random() * 6 })
		end
	end
	local function aura(cf: CFrame, size: Vector3, props)
		local a = anchor(self.Folder, cf, size)
		local e = emitter(a, props)
		self:Track(e, cf.Position, 160)
		m.Destroying:Connect(function()
			a:Destroy()
		end)
		return e
	end
	if id == "BoostPad" then
		aura(base * CFrame.new(0, 0.8, 0), Vector3.new(4, 0.2, 8), {
			Texture = TEX.Streak, Rate = 10, Lifetime = NumberRange.new(0.35, 0.5),
			Speed = NumberRange.new(14, 18), EmissionDirection = Enum.NormalId.Front,
			Size = seq(0.6, 0.1), LightEmission = 1, Orientation = Enum.ParticleOrientation.VelocityParallel,
			Color = ColorSequence.new(Color3.fromRGB(255, 190, 60), Color3.fromRGB(255, 90, 40)), Transparency = seq(0.2, 1),
		})
	elseif id == "TeleportGate" then
		for _, z in { 2.2, -2.2 } do
			aura(base * CFrame.new(0, 3, z), Vector3.new(4, 4, 0.2), {
				Texture = TEX.Star, Rate = 14, Lifetime = NumberRange.new(0.6, 1), Speed = NumberRange.new(0.2, 1),
				Size = seq(0.5, 0), LightEmission = 1, RotSpeed = NumberRange.new(180, 360),
				Color = ColorSequence.new(z > 0 and Color3.fromRGB(200, 120, 255) or Color3.fromRGB(110, 230, 255)),
				Transparency = seq(0.1, 1), Shape = Enum.ParticleEmitterShape.Cylinder,
				ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface,
			})
		end
	elseif id == "SkyLeap" then
		aura(base * CFrame.new(0, 7, 0), Vector3.new(6, 12, 6), {
			Texture = TEX.Star, Rate = 12, Lifetime = NumberRange.new(1.2, 2), Speed = NumberRange.new(2, 4),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.6, 0), LightEmission = 1,
			Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 80, 80)),
				ColorSequenceKeypoint.new(0.33, Color3.fromRGB(255, 230, 60)), ColorSequenceKeypoint.new(0.66, Color3.fromRGB(80, 220, 255)),
				ColorSequenceKeypoint.new(1, Color3.fromRGB(200, 100, 255)) }),
			Transparency = seq(0.1, 1),
		})
	elseif rank >= 4 then
		aura(base * CFrame.new(0, 1, 0), Vector3.new(8, 0.2, 8), {
			Texture = TEX.Star, Rate = 2 + rank, Lifetime = NumberRange.new(1, 1.6), Speed = NumberRange.new(1, 2.5),
			EmissionDirection = Enum.NormalId.Top, Size = seq(0.5, 0), LightEmission = 1,
			Color = ColorSequence.new(TIER_COLOR[piece.tier]), Transparency = seq(0.15, 1),
		})
	end
end

-- ------------------------------------------------------------------ cars
local CAR_STYLE = {
	Rocket = { fire = { Vector3.new(-0.45, 0.75, 2.35), Vector3.new(0.45, 0.75, 2.35) }, glow = Color3.fromRGB(255, 150, 40) },
	Hover = { under = Color3.fromRGB(90, 230, 255), glow = Color3.fromRGB(90, 230, 255) },
	Sports = { under = Color3.fromRGB(255, 80, 150) },
	F1 = { streak = Color3.fromRGB(255, 70, 60) },
	Monster = { dust = 2 },
}

function WorldFX:Car(car: Instance)
	if not car:IsA("Model") or self.Cars[car] then
		return
	end
	local root = car:WaitForChild("Root", 5) :: BasePart?
	if not root then
		return
	end
	local carId = car:GetAttribute("CarId")
	local style = CAR_STYLE[carId or ""] or {}
	local state = { root = root, last = root.CFrame, vel = Vector3.zero, air = 0, emitters = {} }
	local function att(pos: Vector3)
		local a = Instance.new("Attachment")
		a.Position = pos
		a.Parent = root
		return a
	end
	-- exhaust puffs for wheeled cars
	if carId ~= "Hover" then
		local e = emitter(att(Vector3.new(0.4, 0.4, 2.0)), {
			Texture = TEX.Smoke, Rate = 6, Lifetime = NumberRange.new(0.4, 0.7), Speed = NumberRange.new(1, 2),
			EmissionDirection = Enum.NormalId.Back, Size = seq(0.25, 0.9), Transparency = seq(0.55, 1),
			Color = ColorSequence.new(Color3.fromRGB(235, 235, 240)), Drag = 2,
		})
		table.insert(state.emitters, e)
	end
	for _, pos in style.fire or {} do
		local a = att(pos)
		table.insert(state.emitters, emitter(a, {
			Texture = TEX.Fire, Rate = 40, Lifetime = NumberRange.new(0.12, 0.22), Speed = NumberRange.new(5, 8),
			EmissionDirection = Enum.NormalId.Back, Size = seq(0.5, 0.05), LightEmission = 1,
			Color = ColorSequence.new(Color3.fromRGB(255, 240, 150), Color3.fromRGB(255, 90, 30)), Transparency = seq(0, 1),
		}))
	end
	if style.under then
		table.insert(state.emitters, emitter(att(Vector3.new(0, 0.1, 0)), {
			Texture = TEX.Star, Rate = 12, Lifetime = NumberRange.new(0.3, 0.5), Speed = NumberRange.new(0.5, 1.5),
			EmissionDirection = Enum.NormalId.Bottom, Size = seq(0.35, 0), LightEmission = 1,
			Color = ColorSequence.new(style.under), Transparency = seq(0.1, 1),
		}))
	end
	if style.glow or style.under then
		local l = Instance.new("PointLight")
		l.Color = style.glow or style.under
		l.Range = 7
		l.Brightness = 1.2
		l.Shadows = false
		l.Parent = root
	end
	-- sparks when cornering hard and dust when landing (fired by Step)
	state.sparks = emitter(att(Vector3.new(0, 0.1, 1.2)), {
		Texture = TEX.Streak, Rate = 0, Lifetime = NumberRange.new(0.15, 0.3), Speed = NumberRange.new(6, 12),
		SpreadAngle = Vector2.new(40, 40), EmissionDirection = Enum.NormalId.Back, Size = seq(0.3, 0),
		LightEmission = 1, Orientation = Enum.ParticleOrientation.VelocityParallel, Acceleration = Vector3.new(0, -30, 0),
		Color = ColorSequence.new(Color3.fromRGB(255, 240, 160), Color3.fromRGB(255, 140, 40)), Transparency = seq(0, 1),
	})
	state.dust = emitter(att(Vector3.new(0, 0, 0)), {
		Texture = TEX.Smoke, Rate = 0, Lifetime = NumberRange.new(0.4, 0.7), Speed = NumberRange.new(3, 6),
		SpreadAngle = Vector2.new(80, 10), EmissionDirection = Enum.NormalId.Top, Size = seq(0.6, 1.6),
		Color = ColorSequence.new(Color3.fromRGB(230, 225, 215)), Transparency = seq(0.4, 1), Drag = 3,
	})
	self.Cars[car] = state
	car.Destroying:Connect(function()
		self.Cars[car] = nil
	end)
end

-- ------------------------------------------------------------------ per frame
function WorldFX:Step(dt: number)
	self.T += dt
	local t = self.T
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local low = self:Low()

	-- golden die
	local die = self.Die
	if die and die.model.Parent and (camPos - die.base.Position).Magnitude < 500 then
		die.spin += dt * 0.6
		local extra = CFrame.identity
		if die.roll then
			local k = math.clamp((t - die.roll.start) / 1.1, 0, 1)
			local e = 1 - (1 - k) ^ 3
			extra = CFrame.Angles(die.roll.ax * e * math.pi * 2, 0, die.roll.az * e * math.pi * 2)
			if k >= 1 then
				die.roll = nil
			end
		elseif t > die.next then
			die.next = t + 7 + math.random() * 4
			die.roll = { start = t, ax = math.random(1, 2), az = math.random(0, 1) }
			die.sparkle:Emit(low and 10 or 30)
		end
		local bob = math.sin(t * 1.4) * 0.9
		die.model:PivotTo(CFrame.new(die.base.Position + Vector3.new(0, bob, 0))
			* CFrame.Angles(0, die.spin, 0) * (die.base - die.base.Position) * extra)
		die.anchor.CFrame = CFrame.new(die.base.Position + Vector3.new(0, bob, 0))
	end

	-- stall holograms
	for _, sp in self.Spinners do
		if (camPos - sp.base.Position).Magnitude > 320 then
			continue
		end
		local bob = math.sin(t * 1.6 + sp.phase) * 0.6
		if sp.kind == "model" then
			sp.obj:PivotTo(sp.base * CFrame.new(0, bob, 0) * CFrame.Angles(0, t * 0.9, 0))
		elseif sp.kind == "ring" then
			sp.obj.CFrame = sp.base * CFrame.new(0, 0, 0)
			sp.obj.Transparency = 0.45 + math.sin(t * 3 + sp.phase) * 0.15
		elseif sp.kind == "billboard" then
			sp.obj.CFrame = sp.base * CFrame.new(0, bob, 0)
			sp.img.Rotation = math.sin(t * 1.3 + sp.phase) * 10
			if t > sp.next then
				-- cycle through the items this stall sells
				sp.next = t + 2.5
				sp.i = sp.i % #sp.list + 1
				sp.img.Image = sp.list[sp.i].image or sp.img.Image
			end
		end
	end

	-- clouds (wrap around the world)
	for _, c in self.Clouds do
		local p = c.part.Position
		local x = p.X + c.speed * dt
		if x > 1150 then
			x = -1150
		end
		c.part.CFrame = c.part.CFrame.Rotation + Vector3.new(x, p.Y, p.Z)
	end
	for _, b in self.Bobbers do
		b.part.CFrame = b.base * CFrame.new(0, math.sin(t * 0.5 + b.phase) * b.amp, 0) * CFrame.Angles(0, t * b.spin, 0)
	end
	for _, tx in self.Textures do
		tx.tex.OffsetStudsU = (t * tx.du) % 1000
		tx.tex.OffsetStudsV = (t * tx.dv) % 1000
	end

	-- flags
	for _, f in self.Flags do
		if (camPos - f.base.Position).Magnitude < 220 then
			local w = math.sin(t * 3 + f.phase) * 0.25 + math.sin(t * 7.3 + f.phase) * 0.06
			-- hinge on the pole side of the flag
			f.part.CFrame = f.base * CFrame.new(0, 0, 2.25) * CFrame.Angles(0, w, 0) * CFrame.new(0, 0, -2.25)
		end
	end

	-- seagulls circle and flap
	for _, b in self.Birds do
		local a = t * b.speed + b.phase
		local pos = b.center + Vector3.new(math.cos(a) * b.radius, b.height + math.sin(t * 0.7 + b.phase) * 4,
			math.sin(a) * b.radius)
		if (camPos - pos).Magnitude < 700 then
			local dir = Vector3.new(-math.sin(a), 0, math.cos(a)) * math.sign(b.speed)
			local cf = CFrame.lookAt(pos, pos + dir) * CFrame.Angles(0, 0, math.sin(a * 2) * 0.25)
			local flap = math.sin(t * 9 + b.phase) * 0.6
			b.body.CFrame = cf
			b.beak.CFrame = cf * CFrame.new(0, 0, -1.55)
			b.wl.CFrame = cf * CFrame.new(-0.45, 0.2, 0) * CFrame.Angles(0, 0, flap) * CFrame.new(-1.4, 0, 0)
			b.wr.CFrame = cf * CFrame.new(0.45, 0.2, 0) * CFrame.Angles(0, 0, -flap) * CFrame.new(1.4, 0, 0)
		end
	end

	-- butterflies flutter around the flower beds
	if not low then
		for _, b in self.Butterflies do
			local k = t * 0.6 + b.phase
			local pos = b.home + Vector3.new(math.sin(k) * 4 + math.sin(k * 2.3) * 1.5, 1.5 + math.sin(k * 3.1) * 1.2,
				math.cos(k * 1.3) * 4)
			b.part.Position = pos
			b.img.Size = UDim2.fromScale(0.25 + math.abs(math.sin(t * 14 + b.phase)) * 0.75, 1)
		end
	end

	-- pulsing glow on track tiles
	for i = #self.Glows, 1, -1 do
		local g = self.Glows[i]
		if not g.part.Parent then
			table.remove(self.Glows, i)
		elseif (camPos - g.part.Position).Magnitude < 160 then
			local k = (math.sin(t * g.speed * 2 + g.phase) + 1) / 2
			g.part.Color = g.color:Lerp(Color3.new(1, 1, 1), k * 0.45)
		end
	end

	-- cull emitters far away, thin them out on Low
	self.CullT = (self.CullT or 0) + dt
	if self.CullT > 0.25 then
		self.CullT = 0
		for i = #self.Emitters, 1, -1 do
			local em = self.Emitters[i]
			if not em.e.Parent then
				table.remove(self.Emitters, i)
			else
				local on = (camPos - em.pos).Magnitude < em.range
				em.e.Enabled = on
				em.e.Rate = low and em.rate * 0.4 or em.rate
			end
		end
	end

	-- cars: sparks on hard turns, dust on landings, effects off when far or idle
	for car, s in self.Cars do
		if not s.root.Parent then
			self.Cars[car] = nil
			continue
		end
		local cf = s.root.CFrame
		local near = (camPos - cf.Position).Magnitude < 150
		local moved = cf.Position - s.last.Position
		local speed = moved.Magnitude / math.max(dt, 1e-3)
		local teleported = moved.Magnitude > 12
		for _, e in s.emitters do
			e.Enabled = near and speed > 1 and not low or (near and speed > 1 and e.Rate > 20)
		end
		if near and not teleported and speed > 2 then
			local turn = s.last.LookVector:Cross(cf.LookVector).Magnitude / math.max(dt, 1e-3)
			if turn > 2.2 and not low then
				s.sparks:Emit(2)
			end
			local vy = moved.Y / math.max(dt, 1e-3)
			if s.vy and s.vy < -6 and vy > -1 then
				s.dust:Emit(low and 4 or 10)
			end
			s.vy = vy
		end
		s.last = cf
	end
end

function WorldFX:Destroy()
	for _, c in self.Connections do
		c:Disconnect()
	end
	self.Folder:Destroy()
end

return WorldFX

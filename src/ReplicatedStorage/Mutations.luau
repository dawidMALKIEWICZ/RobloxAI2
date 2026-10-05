-- Client look of track mutations (Golden, Frozen, Diamond, Neon, Rainbow, Void):
--   * apply(model, id)   recolours a tile model (palette texture swap + glow colour)
--   * badge(parent, id)  a small coloured tag for cards and reveals
--   * startWorld(map)    sparkles, lights and colour cycling on mutated tiles near the camera
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

local Stats = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Stats"))

local Mutations = {}

local RAINBOW = {
	Color3.fromHex("#ff3b3b"), Color3.fromHex("#ff9f1a"), Color3.fromHex("#ffe03b"),
	Color3.fromHex("#4bdc5a"), Color3.fromHex("#3bd1ff"), Color3.fromHex("#7b5cff"),
	Color3.fromHex("#ff4fd8"),
}
local SPARK = "rbxasset://textures/particles/sparkles_main.dds"
local GLOW = "rbxasset://textures/particles/fire_main.dds"

function Mutations.info(id: string?)
	return if id then Stats.Mutations[id] else nil
end

-- main colour of a mutation; Rainbow cycles with time
function Mutations.color(id: string?, t: number?): Color3
	local m = Mutations.info(id)
	if not m then
		return Color3.new(1, 1, 1)
	end
	if m.color == "rainbow" then
		return Color3.fromHSV(((t or os.clock()) * 0.25) % 1, 0.75, 1)
	end
	return Color3.fromHex(m.color)
end

function Mutations.sequence(id: string?): ColorSequence
	local m = Mutations.info(id)
	if not m then
		return ColorSequence.new(Color3.new(1, 1, 1))
	end
	if m.color == "rainbow" then
		local keys = {}
		for i, c in RAINBOW do
			table.insert(keys, ColorSequenceKeypoint.new((i - 1) / (#RAINBOW - 1), c))
		end
		return ColorSequence.new(keys)
	end
	return ColorSequence.new(Color3.fromHex(m.color), Color3.fromHex(m.color2 or m.color))
end

-- recolours a (cloned) tile model on the client, the same way the server does
function Mutations.apply(model: Instance, id: string?)
	local m = Mutations.info(id)
	if not m then
		return
	end
	model:SetAttribute("Mutation", id)
	local glow = Color3.fromHex(m.glow or "#ffffff")
	for _, p in model:GetDescendants() do
		if p:IsA("MeshPart") then
			if p.Material == Enum.Material.Neon then
				p.Color = glow
			elseif p.TextureID ~= "" and m.texture then
				p.TextureID = m.texture
			end
		end
	end
end

-- "GOLDEN" style tag with a gradient fill, stroke and a slow shimmer
function Mutations.badge(parent: GuiObject, id: string?, props: { [string]: any }?): TextLabel?
	local m = Mutations.info(id)
	local old = parent:FindFirstChild("MutationBadge")
	if old then
		old:Destroy()
	end
	if not m then
		return nil
	end
	local lbl = Instance.new("TextLabel")
	lbl.Name = "MutationBadge"
	lbl.AnchorPoint = Vector2.new(0, 0)
	lbl.Position = UDim2.fromOffset(8, 8)
	lbl.Size = UDim2.fromOffset(96, 26)
	lbl.BackgroundColor3 = Color3.new(1, 1, 1)
	lbl.Text = string.upper(m.name)
	lbl.TextScaled = true
	lbl.FontFace = Font.new("rbxasset://fonts/families/FredokaOne.json", Enum.FontWeight.Bold)
	lbl.TextColor3 = Color3.new(1, 1, 1)
	lbl.ZIndex = 20
	if props then
		for k, v in props do
			(lbl :: any)[k] = v
		end
	end
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0.5, 0)
	corner.Parent = lbl
	local grad = Instance.new("UIGradient")
	grad.Color = Mutations.sequence(id)
	grad.Rotation = 20
	grad.Parent = lbl
	local stroke = Instance.new("UIStroke")
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual
	stroke.Thickness = 2
	stroke.Color = Color3.fromHex("#15131f")
	stroke.Parent = lbl
	local pad = Instance.new("UIPadding")
	pad.PaddingLeft = UDim.new(0, 6)
	pad.PaddingRight = UDim.new(0, 6)
	pad.PaddingTop = UDim.new(0, 2)
	pad.PaddingBottom = UDim.new(0, 2)
	pad.Parent = lbl
	lbl.Parent = parent
	-- shimmer: the gradient slides back and forth while the badge is on screen
	task.spawn(function()
		while lbl.Parent do
			if lbl.Visible then
				grad.Offset = Vector2.new(math.sin(os.clock() * 2) * 0.35, 0)
			end
			task.wait(1 / 20)
		end
	end)
	return lbl
end

-- ------------------------------------------------------------------ world effects
type Entry = { model: Model, mut: string, anchor: BasePart?, emitter: ParticleEmitter?, light: PointLight?,
	glows: { BasePart }, on: boolean }

local entries: { [Model]: Entry } = {}
local quality = "High"

function Mutations.SetQuality(q: string)
	quality = q
end

local function centreOf(model: Model): BasePart?
	local hit = model:FindFirstChild("Hitbox")
	if hit and hit:IsA("BasePart") then
		return hit
	end
	return model:FindFirstChildWhichIsA("BasePart")
end

local function build(e: Entry)
	local m = Mutations.info(e.mut)
	local anchor = centreOf(e.model)
	if not m or not anchor then
		return
	end
	local att = Instance.new("Attachment")
	att.Name = "MutationFX"
	att.Position = Vector3.new(0, 1.2, 0)
	att.Parent = anchor
	local em = Instance.new("ParticleEmitter")
	em.Name = "MutationSparkles"
	em.Texture = if e.mut == "Void" then GLOW else SPARK
	em.Color = Mutations.sequence(e.mut)
	em.LightEmission = if e.mut == "Void" then 0.2 else 0.9
	em.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.3, 0.55),
		NumberSequenceKeypoint.new(1, 0) })
	em.Transparency = NumberSequence.new(0.15, 1)
	em.Lifetime = NumberRange.new(1, 1.8)
	em.Speed = NumberRange.new(0.6, 2)
	em.SpreadAngle = Vector2.new(180, 180)
	em.Acceleration = if e.mut == "Void" then Vector3.new(0, -1, 0) else Vector3.new(0, 1.5, 0)
	em.Rate = ({ Golden = 3, Frozen = 4, Diamond = 5, Neon = 5, Rainbow = 7, Void = 8 })[e.mut] or 4
	em.Shape = Enum.ParticleEmitterShape.Box
	em.ShapeInOut = Enum.ParticleEmitterShapeInOut.Outward
	em.Parent = att
	-- Box shape uses the part size: a thin layer over the whole tile
	e.emitter = em
	e.anchor = anchor
	if e.mut ~= "Golden" and e.mut ~= "Frozen" then
		local light = Instance.new("PointLight")
		light.Color = Mutations.color(e.mut)
		light.Range = 12
		light.Brightness = if e.mut == "Void" then 2 else 1.2
		light.Shadows = false
		light.Parent = att
		e.light = light
	end
	for _, p in e.model:GetDescendants() do
		if p:IsA("MeshPart") and p.Material == Enum.Material.Neon then
			table.insert(e.glows, p)
		end
	end
end

local function track(model: Instance)
	if not model:IsA("Model") or entries[model] then
		return
	end
	local mut = model:GetAttribute("Mutation")
	if type(mut) ~= "string" or not Stats.Mutations[mut] then
		return
	end
	local e: Entry = { model = model, mut = mut, glows = {}, on = true }
	entries[model] = e
	build(e)
	model.AncestryChanged:Connect(function(_, parent)
		if not parent then
			entries[model] = nil
		end
	end)
end

function Mutations.startWorld(map: Instance)
	local plots = map:WaitForChild("Plots")
	local function hookPlot(plot: Instance)
		local folder = plot:WaitForChild("Track", 10)
		if not folder then
			return
		end
		for _, m in folder:GetChildren() do
			track(m)
		end
		folder.ChildAdded:Connect(function(m)
			task.defer(track, m)
		end)
	end
	for _, plot in plots:GetChildren() do
		task.spawn(hookPlot, plot)
	end
	plots.ChildAdded:Connect(hookPlot)
	-- culling + Rainbow colour cycling, a few times per second (cheap)
	local acc = 0
	RunService.Heartbeat:Connect(function(dt)
		acc += dt
		local cam = Workspace.CurrentCamera
		if not cam then
			return
		end
		local now = os.clock()
		local check = acc >= 0.4
		if check then
			acc = 0
		end
		local camPos = cam.CFrame.Position
		local range = if quality == "Low" then 90 else 170
		for _, e in entries do
			local anchor = e.anchor
			if not anchor then
				continue
			end
			if check then
				local on = (anchor.Position - camPos).Magnitude < range
				if on ~= e.on then
					e.on = on
					if e.emitter then
						e.emitter.Enabled = on
					end
					if e.light then
						e.light.Enabled = on and quality ~= "Low"
					end
				end
			end
			if e.on and e.mut == "Rainbow" then
				local c = Mutations.color("Rainbow", now)
				for _, g in e.glows do
					g.Color = c
				end
				if e.light then
					e.light.Color = c
				end
			elseif e.on and e.mut == "Void" and e.light then
				e.light.Brightness = 1.6 + math.sin(now * 3) * 0.8
			end
		end
	end)
end

return Mutations

-- Small rotating 3D island previews for the Island Styles shop cards.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Assets = ReplicatedStorage:WaitForChild("Assets")

local StylePreview = {}
local SCALE = 0.1
local cameras: { [Camera]: GuiObject } = {}
local angle = 0

-- island grass/cliff/shore recoloured like PlotService.applyStyle, plus the style's decor
function StylePreview.Render(vp: ViewportFrame, styleId: string)
	if vp:GetAttribute("Style") == styleId then
		return
	end
	local style = Assets.IslandStyles:FindFirstChild(styleId)
	local base = Assets:FindFirstChild("IslandPreview")
	if not style or not base then
		return
	end
	vp:ClearAllChildren()
	local world = Instance.new("WorldModel")
	world.Parent = vp
	local island = base:Clone()
	for _, p in island:GetDescendants() do
		if p:IsA("BasePart") then
			local role = p:GetAttribute("Role")
			if role and style:GetAttribute(role .. "Color") then
				p.Color = Color3.fromHex(style:GetAttribute(role .. "Color"))
			end
		end
	end
	island.Parent = world
	local decor = style:FindFirstChild("Decor")
	if decor then
		local d = decor:Clone()
		for _, p in d:GetDescendants() do
			if p:IsA("BasePart") then
				p.Size *= SCALE
				p.CFrame = CFrame.new(p.Position * SCALE) * p.CFrame.Rotation
			end
		end
		d.Parent = world
	end
	local cam = Instance.new("Camera")
	cam.FieldOfView = 34
	cam.Parent = vp
	vp.CurrentCamera = cam
	vp:SetAttribute("Style", styleId)
	cameras[cam] = vp
	cam.Destroying:Connect(function()
		cameras[cam] = nil
	end)
end

RunService.RenderStepped:Connect(function(dt)
	angle += dt * 0.35
	for cam, vp in cameras do
		-- only while the viewport is really on screen (its window can be closed)
		local gui = vp:FindFirstAncestorWhichIsA("LayerCollector")
		local window = vp:FindFirstAncestor("StyleShopWindow")
		if vp.Visible and gui and gui.Enabled and (not window or (window :: GuiObject).Visible) then
			local k = angle + (vp:GetAttribute("Phase") or 0)
			cam.CFrame = CFrame.lookAt(Vector3.new(math.sin(k) * 27, 16, math.cos(k) * 27), Vector3.new(0, -1, 0))
		end
	end
end)

return StylePreview

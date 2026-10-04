-- Real track geometry for discovered cards and black silhouettes for undiscovered cards.
local Preview={}
function Preview.Render(card,template,known)
 local vp=card:FindFirstChild("ModelPreview")
 if not vp then
  vp=Instance.new("ViewportFrame")
  vp.Name="ModelPreview"
  vp.BackgroundTransparency=1
  vp.Size=UDim2.new(1,-12,0,136)
  vp.Position=UDim2.new(.5,0,0,30)
  vp.AnchorPoint=Vector2.new(.5,0)
  vp.ZIndex=2
  vp.Ambient=Color3.fromRGB(210,210,210)
  vp.LightColor=Color3.new(1,1,1)
  vp.LightDirection=Vector3.new(-1,-1,-1)
  vp.Parent=card
 end
 if not template then return end
 if vp:GetAttribute("PieceId")==template.Name and vp:GetAttribute("Discovered")==known and vp.CurrentCamera then return end
 vp:ClearAllChildren()
 local world=Instance.new("WorldModel") world.Parent=vp
 local model=template:Clone()
 local path=model:FindFirstChild("Path") if path then path:Destroy() end
 for _,v in model:GetDescendants() do
  if v:IsA("BasePart") then
   v.Anchored=true v.CanCollide=false
   if not known then
    v.Color=Color3.new(0,0,0) v.Material=Enum.Material.SmoothPlastic
    v.Reflectance=0 v.MaterialVariant=""
    if v:IsA("MeshPart") then v.TextureID="" end
   end
  elseif v:IsA("LuaSourceContainer") or v:IsA("Light") or v:IsA("ParticleEmitter") or v:IsA("Beam") or v:IsA("Trail") then
   v:Destroy()
  elseif not known then
   if v:IsA("Decal") or v:IsA("Texture") or v:IsA("SurfaceAppearance") or v:IsA("SurfaceGui") or v:IsA("BillboardGui") then v:Destroy()
   elseif v:IsA("SpecialMesh") then v.TextureId="" v.VertexColor=Vector3.zero end
  end
 end
 model.Parent=world
 local cf,size=model:GetBoundingBox()
 local camera=Instance.new("Camera") camera.FieldOfView=40 camera.Parent=vp
 local direction=Vector3.new(.55,.64,.68).Unit
 local orientation=CFrame.lookAt(cf.Position+direction,cf.Position)
 local aspect=194/136
 local vertical=math.tan(math.rad(camera.FieldOfView/2))
 local distance=0
 -- Fit every bounding-box corner to the card rather than using a fixed zoom.
 for _,x in {-1,1} do for _,y in {-1,1} do for _,z in {-1,1} do
  local point=cf:PointToWorldSpace(size*Vector3.new(x,y,z)/2)
  local relative=orientation:VectorToObjectSpace(point-cf.Position)
  distance=math.max(distance,relative.Z+math.abs(relative.Y)/vertical,relative.Z+math.abs(relative.X)/(vertical*aspect))
 end end end
 camera.CFrame=CFrame.lookAt(cf.Position+direction*math.max(distance*1.06,4),cf.Position)
 vp.CurrentCamera=camera
 vp:SetAttribute("PieceId",template.Name)
 vp:SetAttribute("Discovered",known)
end
return Preview
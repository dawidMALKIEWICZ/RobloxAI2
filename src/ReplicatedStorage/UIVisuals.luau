
local Visuals={}
local GameData=require(game:GetService("ReplicatedStorage").Shared.GameData)
local TweenService=game:GetService("TweenService")
local UserInputService=game:GetService("UserInputService")
local function paint(hex,color)
 if not hex then return end
 for _,band in hex:GetChildren() do
  if band:IsA("Frame") then
   local fraction=tonumber(string.match(band.Name,"%d+")) or 0
   local brightness=1-fraction/220
   band.BackgroundColor3=Color3.new(color.R*brightness,color.G*brightness,color.B*brightness)
  end
 end
end
function Visuals.RefreshSkills(tree,selected,upgrades,cash)
 -- Discover only the next purchase in each branch; purchased nodes stay visible.
 for _,upgrade in GameData.Upgrades do
  local discovered=upgrades[upgrade.id]==true or not upgrade.requires or upgrades[upgrade.requires]==true
  local node=tree:FindFirstChild("Node_"..upgrade.id)
  if node then node.Visible=discovered end
  local line=tree:FindFirstChild("Line_"..upgrade.id)
  local parent=upgrade.requires and tree:FindFirstChild("Node_"..upgrade.requires)
  if line then line.Visible=discovered and parent~=nil and parent.Visible end
 end
 for _,node in tree:GetChildren() do
  if node:IsA("GuiButton") and string.sub(node.Name,1,5)=="Node_" then
   local id=string.sub(node.Name,6)
   local owned=upgrades[id]==true
   local available=not node.Locked.Visible
   local sprite=node:FindFirstChild("HexSprite")
   if sprite then
    sprite.Size=if id==selected then UDim2.fromOffset(164,141) else UDim2.fromOffset(156,134)
    sprite.ImageColor3=owned and Color3.fromRGB(185,255,195) or Color3.new(1,1,1)
   end
   local image=node.Icon:FindFirstChild("AtlasImage")
   if image then image.ImageTransparency=if available or owned then 0 else .28 end
   node.NameText.TextColor3=if available or owned then Color3.new(1,1,1) else Color3.fromRGB(173,191,218)
   node:SetAttribute("Purchased",owned)
   node.Level.Visible=true
   node.Level.BackgroundColor3=owned and Color3.fromRGB(29,109,57) or Color3.fromRGB(24,35,57)
   node.Level.BackgroundTransparency=owned and .08 or .16
   node.Owned.Visible=owned
   node.Owned.BackgroundColor3=Color3.fromRGB(50,218,105)
   if owned then node.Level.Text="OWNED" node.Level.TextColor3=Color3.fromRGB(206,255,208)
   else node.Level.TextColor3=Color3.fromRGB(243,247,255) end
   local connector=tree:FindFirstChild("Line_"..id)
   if connector then connector.BackgroundColor3=owned and Color3.fromRGB(111,234,145) or Color3.fromRGB(74,85,120) end
  end
 end
end
function Visuals.Bind(gui)
 local root=gui.Root local hud=root.HUD local panel=root.BuildPanel
 local win=root.Windows.SkillsWindow local tree=win.Body.Tree local inf=win.Body.Info
 local function center()
  local size=tree.AbsoluteWindowSize
  local s=root.Scale.Scale
  local centerX=tree:GetAttribute("CenterX") or 1100
  tree.CanvasPosition=Vector2.new(math.max(0,centerX*s-size.X/2),math.max(0,600*s-size.Y/2))
 end
 local function fitWidth()
  local s=root.Scale.Scale
  local virtualWidth=tree.AbsoluteWindowSize.X/s
  local shift=math.max(0,virtualWidth/2-1100)
  local prior=tree:GetAttribute("CenterShift") or 0
  for _,d in tree:GetChildren() do
   if d:IsA("GuiObject") and (string.sub(d.Name,1,5)=="Node_" or string.sub(d.Name,1,5)=="Line_") then
    d.Position=UDim2.fromOffset(d.Position.X.Offset+shift-prior,d.Position.Y.Offset)
   end
  end
  tree:SetAttribute("CenterShift",shift)
  tree:SetAttribute("CenterX",1100+shift)
  tree.CanvasSize=UDim2.fromOffset(math.max(2400,virtualWidth),1320)
 end
 local function sync()
  hud.Visible=not win.Visible
  hud.RollArea.Visible=not panel.Visible
  hud.Stats.Visible=not panel.Visible
  hud.Earnings.Visible=not panel.Visible
 end
 win:GetPropertyChangedSignal("Visible"):Connect(function()
  sync()
  if win.Visible then inf.Visible=false task.defer(function() fitWidth() center() end) end
 end)
 panel:GetPropertyChangedSignal("Visible"):Connect(sync)
 inf.Dismiss.Activated:Connect(function() inf.Visible=false end)
 win.Header.CenterButton.Activated:Connect(function() inf.Visible=false center() end)
 root.Scale:GetPropertyChangedSignal("Scale"):Connect(function()
  if win.Visible then task.defer(function() fitWidth() center() end) end
 end)
 local dragging=false local startPointer=nil local startCanvas=nil
 tree.InputBegan:Connect(function(input)
  if input.UserInputType==Enum.UserInputType.MouseButton1 then
   dragging=true startPointer=Vector2.new(input.Position.X,input.Position.Y) startCanvas=tree.CanvasPosition
  end
 end)
 UserInputService.InputChanged:Connect(function(input)
  if dragging and win.Visible and input.UserInputType==Enum.UserInputType.MouseMovement then
   local delta=Vector2.new(input.Position.X,input.Position.Y)-startPointer
   local max=tree.AbsoluteCanvasSize-tree.AbsoluteWindowSize
   tree.CanvasPosition=Vector2.new(math.clamp(startCanvas.X-delta.X,0,math.max(0,max.X)),math.clamp(startCanvas.Y-delta.Y,0,math.max(0,max.Y)))
  end
 end)
 UserInputService.InputEnded:Connect(function(input)
  if input.UserInputType==Enum.UserInputType.MouseButton1 then dragging=false end
 end)
 local items=panel.Items
 local function scroll(direction)
  local max=math.max(0,items.AbsoluteCanvasSize.X-items.AbsoluteWindowSize.X)
  local target=Vector2.new(math.clamp(items.CanvasPosition.X+direction*630,0,max),0)
  TweenService:Create(items,TweenInfo.new(.2,Enum.EasingStyle.Quad),{CanvasPosition=target}):Play()
 end
 panel.Prev.Activated:Connect(function() scroll(-1) end)
 panel.Next.Activated:Connect(function() scroll(1) end)
 sync()
end
return Visuals


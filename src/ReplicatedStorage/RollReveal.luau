local ReplicatedStorage=game:GetService("ReplicatedStorage")
local TweenService=game:GetService("TweenService")
local ContentProvider=game:GetService("ContentProvider")
local RunService=game:GetService("RunService")
local Stats=require(ReplicatedStorage.Shared.Stats)
local Format=require(ReplicatedStorage.Shared.Format)
local Tiles=ReplicatedStorage.Assets.Tiles
local Mutations=require(ReplicatedStorage:WaitForChild("Mutations"))
local Reveal={}
Reveal.__index=Reveal
local COLORS={Common=Color3.fromRGB(111,255,40),Rare=Color3.fromRGB(66,197,255),Epic=Color3.fromRGB(198,83,255),Legendary=Color3.fromRGB(255,204,44),Mythical=Color3.fromRGB(255,60,126),Secret=Color3.fromRGB(220,244,255)}

-- gradient colours for the AUTO / HIDE buttons (same 4-stop look as the other game buttons)
local PALETTE={
 green={Color3.fromRGB(201,255,122),Color3.fromRGB(98,224,38),Color3.fromRGB(44,156,16)},
 blue={Color3.fromRGB(150,220,255),Color3.fromRGB(60,140,255),Color3.fromRGB(30,80,200)},
 purple={Color3.fromRGB(220,170,255),Color3.fromRGB(160,80,255),Color3.fromRGB(100,40,190)},
 orange={Color3.fromRGB(255,220,140),Color3.fromRGB(255,150,40),Color3.fromRGB(210,90,20)},
}
local function paint(button,name)
 local g=button:FindFirstChild("Gradient") local c=PALETTE[name]
 if g and c then g.Color=ColorSequence.new({ColorSequenceKeypoint.new(0,c[1]),ColorSequenceKeypoint.new(.42,c[2]),ColorSequenceKeypoint.new(.58,c[2]),ColorSequenceKeypoint.new(1,c[3])}) end
end
Reveal.Paint=paint

function Reveal:UpdateHUD()
 self.Gui.Root.HUD.Visible=(self.Compact or not self.Frame.Visible) and not self.Gui.Root.Windows.SkillsWindow.Visible local covered=false
 if self.Compact then
  for _,window in self.Gui.Root.Windows:GetChildren() do
   if window:IsA("GuiObject") and window.Visible then covered=true break end
  end
 end
 for _,element in {self.Frame.Reveal,self.Frame.Glow,self.Frame.AutoButton,self.Frame.HideButton} do element.Visible=not covered end
 self.Frame.MiniBackdrop.Visible=false
 self.Frame.Glow.Visible=false

end

function Reveal:SetCompact(compact)
 self.Compact=compact==true
 local frame=self.Frame
 local area=frame.Reveal
 local k=self.Compact and .5 or 1
 frame:SetAttribute("Compact",self.Compact)
 frame.BackgroundTransparency=self.Compact and 1 or .38
 -- Keep menus above the persistent miniature, while full-screen rolls stay in front.
 frame.ZIndex=self.Compact and 0 or 60
 frame.MiniBackdrop.Visible=false
 area.Size=UDim2.fromOffset(780*k,630*k)
 area.Position=self.Compact and UDim2.new(.5,0,0,300) or UDim2.fromScale(.5,.46)
 area.Viewport.Size=UDim2.fromOffset(620*k,430*k)
 area.Odds.Size=UDim2.fromOffset(690*k,104*k)
 area.PieceName.Size=UDim2.fromOffset(780*k,100*k)
 area.New.Size=UDim2.fromOffset(210*k,48*k)
 area.Odds:FindFirstChildOfClass("UIStroke").Thickness=4*k
 area.PieceName:FindFirstChildOfClass("UIStroke").Thickness=4*k
 area.New:FindFirstChildOfClass("UIStroke").Thickness=3*k
 frame.Glow.Position=self.Compact and UDim2.new(.5,0,0,300) or UDim2.fromScale(.5,.44)
 frame.Glow.Layout.Scale=k
 for _,button in {frame.AutoButton,frame.HideButton} do
  button.Size=UDim2.fromOffset(self.Compact and 130 or 220,self.Compact and 110 or 220)
  button.AnchorPoint=Vector2.new(.5,self.Compact and .5 or 1)
  button.ControlSprite.Size=UDim2.fromOffset(self.Compact and 56 or 120,self.Compact and 56 or 120)
  button.ControlSprite.Position=UDim2.fromScale(.5,.38)
  button.Label.Size=UDim2.fromOffset(self.Compact and 146 or 220,self.Compact and 34 or 50)
  button.Label.TextScaled=false
  button.Label.FontFace=Font.new("rbxasset://fonts/families/FredokaOne.json")
  button.Label.TextSize=self.Compact and 26 or 43
  button.Label.Position=UDim2.new(.5,0,1,self.Compact and -17 or -25)
  button.Label:FindFirstChildOfClass("UIStroke").Thickness=self.Compact and 2 or 3
 end
 local sides=area:FindFirstChild("SideTriangles")
 if sides then
  for _,arrow in sides:GetChildren() do
   if arrow:IsA("ImageLabel") then arrow.Size=UDim2.fromOffset(160*k,32*k) end
  end
 end
 frame.AutoButton.Position=self.Compact and UDim2.new(.5,320,0,240) or UDim2.new(.28,0,1,-28)
 frame.HideButton.Position=self.Compact and UDim2.new(.5,320,0,372) or UDim2.new(.72,0,1,-28)
 frame.HideButton.Label.Text=self.Compact and "SHOW" or "HIDE"
 local art=require(ReplicatedStorage.Shared.GameData).UIArt or {}
 frame.HideButton.ControlSprite.Image=art[self.Compact and "icon_eye" or "icon_eyeoff"] or frame.HideButton.ControlSprite.Image
 paint(frame.HideButton,self.Compact and "orange" or "purple")
 self:UpdateHUD()
 -- A compact result stays until the next roll; expanding an idle result resumes dismissal.
 if not self.Compact and not self.Animating and frame.Visible then
  local token=self.Token
  task.delay(.85,function()
   if token==self.Token and not self.Compact and not self.Animating then self:Cancel() end
  end)
 end
end

function Reveal.new(gui)
 local self=setmetatable({Gui=gui,Frame=gui.Root.RollReel,Token=0,Compact=false,Animating=false},Reveal)
 local sides=self.Frame.Reveal:FindFirstChild("SideTriangles") or Instance.new("Folder")
 sides.Name="SideTriangles" sides.Parent=self.Frame.Reveal
 for _,name in {"Left","Right"} do
  local arrow=sides:FindFirstChild(name) or Instance.new("ImageLabel")
  arrow.Name=name arrow.Image="rbxassetid://123194301454534" arrow.BackgroundTransparency=1
  arrow.AnchorPoint=Vector2.new(.5,.5) arrow.Position=UDim2.fromScale(name=="Left" and .09 or .91,.48)
  arrow.Size=UDim2.fromOffset(160,32) arrow.Rotation=name=="Left" and 0 or 180
  arrow.ZIndex=self.Frame.Reveal.ZIndex+2 arrow.Active=false arrow.Parent=sides
 end
 self.Frame.HideButton.Activated:Connect(function() self:SetCompact(not self.Compact) end)
 self.Frame.AutoButton.Activated:Connect(function() if self.OnAuto then self.OnAuto() end end)
 self.Frame:GetPropertyChangedSignal("Visible"):Connect(function()
  if not self.Frame.Visible then self.Token+=1 self.Animating=false end
  self:UpdateHUD()
 end)
 for _,window in gui.Root.Windows:GetChildren() do
  if window:IsA("GuiObject") then window:GetPropertyChangedSignal("Visible"):Connect(function() self:UpdateHUD() end) end
 end
 self:SetCompact(false)
 task.spawn(function()

  pcall(function() ContentProvider:PreloadAsync({self.Frame.AutoButton.ControlSprite,self.Frame.HideButton.ControlSprite,"rbxassetid://123194301454534"}) end)
 end)
 local phase=0
 self.RenderConnection=RunService.RenderStepped:Connect(function(dt)
  if not self.Frame.Visible then return end
  phase+=dt
  if self.Orbs and self.Center then
   for _,o in self.Orbs do
    local a=phase*o.speed+o.phase
    o.part.Position=self.Center+Vector3.new(math.cos(a)*o.radius,o.height+math.sin(a*2)*.8,math.sin(a)*o.radius)
   end
  end
  local camera=self.Frame.Reveal.Viewport.CurrentCamera
  if camera and self.Center and self.Distance then
   local angle=.72+math.sin(phase*.8)*.07
   local d=self.Distance
   camera.CFrame=CFrame.lookAt(self.Center+Vector3.new(math.sin(angle)*d,d*.57,math.cos(angle)*d),self.Center)
  end
 end)
 gui.Destroying:Connect(function() self.RenderConnection:Disconnect() end)
 return self
end
function Reveal:Destroy()
 self:Cancel()
 self.RenderConnection:Disconnect()
end
function Reveal:Cancel()
 self.Token+=1 self.Animating=false self.Frame.Visible=false
 self:UpdateHUD()
end
-- A new manual roll keeps the player's chosen compact/full presentation.
function Reveal:Resume() self:UpdateHUD() end
function Reveal:SetAuto(enabled)
 paint(self.Frame.AutoButton,enabled and "green" or "blue")
 self.Frame.AutoButton.Status.Text=enabled and "ON" or "OFF"
 self.Frame.AutoButton.Label.Text=enabled and "AUTO ON" or "AUTO"
 self.Frame.AutoButton.Label.TextColor3=Color3.new(1,1,1)
 self.Frame.AutoButton.Stroke.Color=Color3.new(0,0,0)
 self.Frame.AutoButton.Stroke.Transparency=0
end
-- glowing orbs circling the rolled tile inside the viewport (Epic and rarer)
function Reveal:AddOrbs(piece)
 local rank=({Common=1,Rare=2,Epic=3,Legendary=4,Mythical=5,Secret=6})[piece.tier] or 1
 self.Orbs={}
 if rank<3 or not self.Center then return end
 local world=self.Frame.Reveal.Viewport:FindFirstChildOfClass("WorldModel") if not world then return end
 local color=COLORS[piece.tier] or COLORS.Common
 local n=rank+3
 for i=1,n do
  local p=Instance.new("Part") p.Shape=Enum.PartType.Ball p.Material=Enum.Material.Neon p.Anchored=true p.CanCollide=false
  p.Size=Vector3.one*(rank>=5 and .9 or .7) p.Color=rank>=6 and Color3.fromHSV(i/n,.6,1) or (i%3==0 and Color3.new(1,1,1) or color)
  p.Parent=world
  self.Orbs[#self.Orbs+1]={part=p,phase=i/n*math.pi*2,radius=6+(i%2)*1.6,height=(i%3)*1.2,speed=rank>=5 and 2.4 or 1.6}
 end
 local ring=Instance.new("Part") ring.Shape=Enum.PartType.Cylinder ring.Material=Enum.Material.Neon ring.Anchored=true ring.CanCollide=false
 ring.Size=Vector3.new(.15,15,15) ring.Color=color ring.Transparency=.55 ring.CFrame=CFrame.new(self.Center-Vector3.new(0,1.2,0))*CFrame.Angles(0,0,math.pi/2)
 ring.Parent=world
end
function Reveal:ShowPiece(piece,mut)
 self.Orbs={}
 local area=self.Frame.Reveal
 local m=mut and Stats.Mutations[mut]
 area.PieceName.Text=(m and m.name.." " or "")..piece.name
 area.Odds.Text="1 in "..Format.short(piece.odds*(m and m.chance or 1))
 local color=COLORS[piece.tier] or COLORS.Common
 area.Odds.TextColor3=m and Mutations.color(mut) or color
 Mutations.badge(area,mut,{Position=UDim2.new(.5,-70,0,4),Size=UDim2.fromOffset(140,34)})
 local vp=area.Viewport
 vp:ClearAllChildren()
 local template=Tiles:FindFirstChild(piece.id)
 if not template then return end
 local world=Instance.new("WorldModel") world.Parent=vp
 local model=template:Clone()
 local path=model:FindFirstChild("Path") if path then path:Destroy() end
 Mutations.apply(model,mut)
 for _,p in model:GetDescendants() do if p:IsA("BasePart") then p.Anchored=true p.CanCollide=false end end
 model.Parent=world
 local cf,size=model:GetBoundingBox()
 local cam=Instance.new("Camera") cam.FieldOfView=38 cam.Parent=vp
 self.Center=cf.Position self.Distance=math.max(12,size.Magnitude*.93)
 cam.CFrame=CFrame.lookAt(cf.Position+Vector3.new(self.Distance*.66,self.Distance*.57,self.Distance*.75),cf.Position)
 vp.CurrentCamera=cam
end
function Reveal:Play(result,fast,rollTime)
 local piece=Stats.Pieces[result.piece]
 if not piece then return end
 if fast then
  if self.Gui.Root.BuildPanel.Visible then return end
  for _,w in self.Gui.Root.Windows:GetChildren() do if w:IsA("GuiObject") and w.Visible then return end end
 end
 self.Token+=1 local token=self.Token
 self.Animating=true
 local frame=self.Frame local area=frame.Reveal
 local color=COLORS[piece.tier] or COLORS.Common
 frame.BackgroundColor3=color:Lerp(Color3.fromRGB(3,13,23),.82)
 frame.MiniBackdrop.BackgroundColor3=color:Lerp(Color3.fromRGB(28,49,75),.65)
 for _,f in frame.Glow:GetChildren() do if f:IsA("Frame") and f.Name:match("^Halo") then f.BackgroundColor3=color end end
 if frame.Glow:FindFirstChild("SoftHalo") then frame.Glow.SoftHalo.ImageColor3=color end
 area.New.Visible=false
 frame.Hint.Text="Rolling..."
 frame.Visible=true self:UpdateHUD()
 if self.VFX then self.VFX:RollStart(self.Compact or fast) end
 local count=fast and 4 or 8
 local duration=math.clamp((rollTime or 2)*.55,fast and .18 or .25,fast and .55 or 1.2)
 for i=1,count do
  if token~=self.Token or not frame.Visible then return end
  self:ShowPiece(Stats.PieceList[math.random(1,#Stats.PieceList)])
  area.Pop.Scale=.88+i/count*.12
  if self.VFX then self.VFX:RollTick(i/count,self.Compact or fast) end
  task.wait(duration*(.5+i/count)/(count+1))
 end
 if token~=self.Token or not frame.Visible then return end
 -- suspense before a big pull: the screen darkens and the reel "heartbeats"
 local rank=({Common=1,Rare=2,Epic=3,Legendary=4,Mythical=5,Secret=6})[piece.tier] or 1
 if rank>=4 and not fast and not self.Compact and self.VFX then
  local wait=({.75,1.1,1.6})[rank-3]
  area.PieceName.Text=rank>=6 and "? ? ?" or "..."
  area.Odds.Text=""
  frame.Hint.Text=rank>=6 and "Something impossible..." or "Something rare is coming..."
  self.VFX:Buildup(rank,color,wait)
  task.wait(wait)
  if token~=self.Token or not frame.Visible then return end
 end
 self:ShowPiece(piece,result.mutation)
 self:AddOrbs(piece)
 if self.VFX then self.VFX:RollResult(piece,result.new==true,self.Compact,fast) end
 -- a mutated pull gets its own shout on top of the rarity effects
 local mut=result.mutation and Stats.Mutations[result.mutation]
 if mut and self.VFX then
  local mc=Mutations.color(result.mutation)
  local v=self.VFX
  task.delay(fast and .05 or .35,function()
   if token~=self.Token then return end
   if not fast and not self.Compact then
    v:Banner(string.upper(mut.name).."!  x"..mut.mult,mc,.7,UDim2.fromScale(.5,.2),1.3,mut.color=="rainbow")
    v:EdgeGlow(mc,3,.9)
   end
   v:UIBurst(v:Point(area.Viewport),mc,v:Q(mut.mult>=4 and 40 or 22),220)
   v:Sound(mut.mult>=6 and "Legendary" or mut.mult>=3 and "Epic" or "Unlock",1.1,.45)
  end)
 end
 area.New.Visible=result.new==true
 area.Pop.Scale=.84
 TweenService:Create(area.Pop,TweenInfo.new(.28,Enum.EasingStyle.Back,Enum.EasingDirection.Out),{Scale=1}):Play()
 self.Animating=false
 frame.Hint.Text=""
 frame:SetAttribute("ResultPiece",piece.id)
 -- Compact results persist until the next roll replaces them; full results dismiss normally.
 local hold=({Common=.85,Rare=1.05,Epic=1.6,Legendary=2.4,Mythical=2.9,Secret=3.6})[piece.tier] or .85
 if mut then hold=math.max(hold,1.5) end
 task.delay(fast and .4 or hold,function()
  if token==self.Token and not self.Compact then self:Cancel() end
 end)
end
return Reveal

-- Presentation only: effects never change inventory, track physics, or purchase results.
local VFX = {}
VFX.__index = VFX
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local ContentProvider = game:GetService("ContentProvider")
local Debris = game:GetService("Debris")
local IMG = {Ring="rbxassetid://134711977820804", Glow="rbxassetid://82400724728274"}
local GameData = require(game:GetService("ReplicatedStorage").Shared.GameData)
local AUDIO = GameData.Audio or {}
-- cue -> {file in GameData.Audio, default volume}
local CUES = {Hover={"hover",.12},Click={"click",.42},Tick={"tick",.3},Whoosh={"whoosh",.32},WindowClose={"window_close",.22},
 RollStart={"roll_start",.45},Common={"common",.5},Rare={"rare",.55},Epic={"epic",.6},Legendary={"legendary",.7},Mythical={"mythical",.75},Secret={"secret",.8},
 Purchase={"purchase",.55},Place={"place",.5},Remove={"remove",.45},Error={"error",.45},Coin={"coin",.22},Teleport={"teleport",.4},Boost={"boost",.35},
 Unlock={"unlock",.5},Potion={"potion",.55},Equip={"equip",.45},Milestone={"milestone",.6},BuildOpen={"build_open",.5}}
local COLORS = {Common=Color3.fromRGB(182,255,132),Rare=Color3.fromRGB(67,203,255),Epic=Color3.fromRGB(195,91,255),Legendary=Color3.fromRGB(255,205,64),Mythical=Color3.fromRGB(255,77,159),Secret=Color3.fromRGB(204,255,251)}
local RANK = {Common=1,Rare=2,Epic=3,Legendary=4,Mythical=5,Secret=6}
local function tween(obj,duration,properties,style,direction)
 local t=TweenService:Create(obj,TweenInfo.new(duration,style or Enum.EasingStyle.Quad,direction or Enum.EasingDirection.Out),properties)
 t:Play() return t
end
local function image(parent,name,asset,size,position,z)
 local i=Instance.new("ImageLabel") i.Name=name i.BackgroundTransparency=1 i.Image=asset
 i.Size=size i.Position=position i.AnchorPoint=Vector2.new(.5,.5) i.ZIndex=parent.Name=="VFXOverlay" and 100+(z or 1) or (z or 1) i.Active=false i.Parent=parent return i
end
local function scaleFor(object,name)
 local s=object:FindFirstChild(name) or Instance.new("UIScale") s.Name=name s.Parent=object return s
end
function VFX:Connect(signal,fn)
 local c=signal:Connect(fn) self.Connections[#self.Connections+1]=c return c
end
function VFX:Sound(name,pitch,volume)
 local cue=CUES[name] if not cue or self.Destroyed or not self.SfxOn then return end
 local now=os.clock()
 local throttle=({Hover=.07,Coin=.12,Error=.25,Tick=.035})[name] or .03
 if now-(self.LastSound[name] or -100)<throttle then return end
 self.LastSound[name]=now
 local pool=self.Pools[name]
 if not pool then
  local id=AUDIO[cue[1]] if not id then return end
  pool={i=0}
  for k=1,(name=="Tick" or name=="Coin" or name=="Click" or name=="Hover") and 4 or 2 do
   local snd=Instance.new("Sound") snd.Name="SFX_"..name snd.SoundId=id snd.SoundGroup=self.SoundGroup snd.Parent=SoundService pool[k]=snd
  end
  self.Pools[name]=pool
 end
 pool.i=pool.i%#pool+1
 local snd=pool[pool.i]
 snd.PlaybackSpeed=pitch or 1 snd.Volume=volume or cue[2]
 snd.TimePosition=0 snd:Play()
 self.Metrics.sounds+=1 self.Gui:SetAttribute("VFXSoundsPlayed",self.Metrics.sounds) self.Gui:SetAttribute("VFXLastSound",name)
end
-- player settings: sound effects, music and effect quality ("High" / "Low")
function VFX:SetSfx(on) self.SfxOn=on~=false self.SoundGroup.Volume=self.SfxOn and .8 or 0 end
function VFX:SetMusic(on)
 self.MusicOn=on~=false
 if not self.Music then return end
 if self.MusicOn then if not self.Music.IsPlaying then self.Music:Play() end tween(self.MusicGroup,1.2,{Volume=.32})
 else tween(self.MusicGroup,.5,{Volume=0}) end
end
function VFX:SetQuality(q) self.Quality=q=="Low" and "Low" or "High" self.Gui:SetAttribute("VFXQuality",self.Quality) end
function VFX:Q(n) return self.Quality=="Low" and math.max(1,math.floor(n*.45)) or n end
function VFX:Point(object)
 return (object.AbsolutePosition+object.AbsoluteSize/2-self.Root.AbsolutePosition)/self.Root.Scale.Scale
end
function VFX:UIBurst(point,color,count,radius)
 if self.Destroyed then return end
 count=math.min(count or 8,72-self.UIAlive) if count<=0 then return end
 self.Metrics.uiBursts+=1
 for n=1,count do
  self.UIAlive+=1
  local size=math.random(6,14)
  local p=image(self.Layer,"Spark",IMG.Glow,UDim2.fromOffset(size,size),UDim2.fromOffset(point.X,point.Y),1)
  p.ImageColor3=n%4==0 and Color3.new(1,1,1) or color p.Rotation=math.random(0,360)
  local a=n/count*math.pi*2+math.random()*.3 local distance=(radius or 80)*(.5+math.random()*.5)
  tween(p,.4+math.random()*.18,{Position=UDim2.fromOffset(point.X+math.cos(a)*distance,point.Y+math.sin(a)*distance+14),Size=UDim2.fromOffset(2,2),ImageTransparency=1,Rotation=p.Rotation+110})
  task.delay(.65,function() p:Destroy() self.UIAlive=math.max(0,self.UIAlive-1) end)
 end
end
function VFX:Ripple(button,color)
 local p=image(button,"ClickRipple",IMG.Ring,UDim2.fromOffset(12,12),UDim2.fromScale(.5,.5),20)
 p.ImageColor3=color or Color3.new(1,1,1) p.ImageTransparency=.32
 local radius=math.min(130,button.AbsoluteSize.X/self.Root.Scale.Scale*.7)
 tween(p,.36,{Size=UDim2.fromOffset(radius,radius),ImageTransparency=1,Rotation=25}) Debris:AddItem(p,.4)
end
function VFX:BindButton(button)
 if button:GetAttribute("VFXBound") then return end button:SetAttribute("VFXBound",true)
 local s=scaleFor(button,"Bounce") local hover=false
 self:Connect(button.MouseEnter,function()
  hover=true tween(s,.16,{Scale=1.045},Enum.EasingStyle.Back)
  if self.LastHoverButton~=button and os.clock()-self.Started>2 then self:Sound("Hover") end
  self.LastHoverButton=button
  if button.BackgroundTransparency<.5 then
   local stroke=button:FindFirstChild("HoverHighlight") or Instance.new("UIStroke")
   stroke.Name="HoverHighlight" stroke.Color=Color3.fromRGB(206,242,255) stroke.Thickness=1.5
   stroke.ApplyStrokeMode=Enum.ApplyStrokeMode.Border stroke.Transparency=1 stroke.Parent=button
   tween(stroke,.15,{Transparency=.45})
  end
 end)
 self:Connect(button.MouseLeave,function()
  hover=false tween(s,.18,{Scale=1})
  local stroke=button:FindFirstChild("HoverHighlight")
  if stroke then tween(stroke,.18,{Transparency=1}) end
 end)
 self:Connect(button.MouseButton1Down,function() tween(s,.07,{Scale=.93}) end)
 self:Connect(button.MouseButton1Up,function() tween(s,.22,{Scale=hover and 1.045 or 1},Enum.EasingStyle.Back) end)
 self:Connect(button.Activated,function() self.LastButton=button self:Sound("Click",.97+math.random()*.06) self:Ripple(button) end)
end
function VFX:Confetti(point,color,count,compact)
 count=math.min(count,72-self.UIAlive)
 for i=1,count do
  self.UIAlive+=1
  local p=Instance.new("Frame") p.Name="Confetti" p.BorderSizePixel=0 p.AnchorPoint=Vector2.new(.5,.5) p.ZIndex=101 p.Active=false
  p.BackgroundColor3=i%4==0 and Color3.new(1,1,1) or color:Lerp(Color3.fromRGB(255,219,98),math.random()*.35)
  p.Size=UDim2.fromOffset(math.random(5,10),math.random(9,17)) p.Position=UDim2.fromOffset(point.X,point.Y) p.Rotation=math.random(-90,90) p.Parent=self.Layer
  local spread=compact and 90 or 310
  tween(p,.26,{Position=UDim2.fromOffset(point.X+(math.random()-.5)*spread*2,point.Y-math.random(45,compact and 100 or 220))},Enum.EasingStyle.Quart)
  task.delay(.26,function()
   if not p.Parent then return end
   tween(p,.8,{Position=p.Position+UDim2.fromOffset((math.random()-.5)*80,compact and 120 or 300),BackgroundTransparency=1,Rotation=p.Rotation+math.random(-240,240)},Enum.EasingStyle.Sine)
  end)
  task.delay(1.15,function() p:Destroy() self.UIAlive=math.max(0,self.UIAlive-1) end)
 end
end
function VFX:Flash(point,color,compact)
 local p=image(self.Layer,"ResultFlash",IMG.Glow,UDim2.fromOffset(80,80),UDim2.fromOffset(point.X,point.Y),0)
 p.ImageColor3=color p.ImageTransparency=.20
 local size=compact and 270 or 770 tween(p,.48,{Size=UDim2.fromOffset(size,size),ImageTransparency=1}) Debris:AddItem(p,.5)
end
function VFX:RollStart(compact)
 self.Metrics.rollStarts+=1 self.Gui:SetAttribute("VFXRollStarts",self.Metrics.rollStarts) self:Sound("Whoosh",compact and 1.12 or 1,compact and .2 or .42)
 local f=self.Root.RollReel
 if f.Glow:FindFirstChild("Sunburst") then f.Glow.Sunburst.ImageTransparency=.95 end
end
function VFX:RollTick(progress,compact)
 if not self.Root.RollReel.Reveal.Visible then return end
 self:Sound("Tick",.85+progress*.5,compact and .16 or .32)
 local f=self.Root.RollReel local viewport=f.Reveal.Viewport
 local s=scaleFor(viewport,"RollTick") s.Scale=.94 tween(s,.11,{Scale=1},Enum.EasingStyle.Back)
end
function VFX:RollResult(piece,isNew,compact,auto)
 self.Metrics.results+=1 self.Gui:SetAttribute("VFXResults",self.Metrics.results) self.Gui:SetAttribute("VFXLastTier",piece.tier)
 if not self.Root.RollReel.Reveal.Visible then return end
 local color=COLORS[piece.tier] or COLORS.Common local rank=RANK[piece.tier] or 1
 local small=compact or auto
 local point=self:Point(self.Root.RollReel.Reveal.Viewport)
 local rays=self.Root.RollReel.Glow:FindFirstChild("Sunburst")
 if rays then rays.ImageColor3=color rays.ImageTransparency=rank>=3 and .84 or .92 end
 self:Flash(point,color,compact)
 self:UIBurst(point,color,self:Q(small and 6 or 10+rank*4),compact and 90 or 250+rank*20)
 if rank>=3 or isNew then self:Confetti(point,color,self:Q(small and 10 or 18+rank*7),compact) end
 self:Sound(({"Common","Rare","Epic","Legendary","Mythical","Secret"})[rank] or "Common",1,small and .3 or nil)
 if isNew and rank<3 then self:Sound("Unlock",1.08,small and .2 or .35) end
 if isNew then self:Banner("NEW!",Color3.fromRGB(111,255,40),small and .55 or .8,UDim2.new(.5,0,.5,small and -120 or -330),.9) end
 if small then
  if rank>=4 then self:Banner(string.upper(piece.tier).."!",color,.6,UDim2.new(.5,0,.5,-60),1) end
  return
 end
 -- the bigger the rarity, the bigger the show
 if rank>=2 then self:Shockwave(point,color,rank>=4 and 3 or 1) end
 if rank>=3 then
  self:Rays(point,color,rank)
  self:EdgeGlow(color,rank)
  local banner=self:Banner(string.upper(piece.tier)..(rank>=5 and "!!" or "!"),color,rank>=5 and 1.35 or 1.1,UDim2.new(.5,0,.5,-360),1.5+rank*.15,rank>=6)
  if rank>=5 then self:Chromatic(banner,1.2+rank*.15) end
  self:CameraPunch(4+rank*2,.6)
  self:Tint(color,.8,rank>=5 and .6 or .4)
  self.ShakeUntil=os.clock()+.2+rank*.06 self.ShakeStrength=.03+rank*.016
 end
 if rank>=4 then
  self:ScreenFlash(rank>=6 and Color3.new(1,1,1) or color,rank>=5 and .15 or .35)
  self:StarRain(color,self:Q(10+rank*6),rank>=6)
  self:LightPillar(color,rank)
 end
 if rank>=5 then task.delay(.45,function() if not self.Destroyed then self:Shockwave(point,Color3.new(1,1,1),2) self:Confetti(point,color,self:Q(30),false) end end) end
 if rank>=6 then
  self:Glitch(1.2)
  task.delay(.9,function() if not self.Destroyed then self:Confetti(point,Color3.fromHSV(math.random(),.7,1),self:Q(40),false) end end)
 end
end
-- tension before a Legendary+ result is shown: darken, heartbeat, rising ticks
function VFX:Buildup(rank,color,duration)
 if self.Destroyed then return end
 local dim=Instance.new("Frame") dim.Name="BuildupDim" dim.BackgroundColor3=Color3.new(0,0,0) dim.BackgroundTransparency=1 dim.BorderSizePixel=0
 dim.Size=UDim2.fromScale(1,1) dim.ZIndex=55 dim.Active=false dim.Parent=self.Root
 tween(dim,duration*.8,{BackgroundTransparency=rank>=6 and .25 or .5})
 self:SpeedLines(duration,color)
 local cam=self:CamFX()
 if cam then
  self.BaseFOV=self.BaseFOV or cam.FieldOfView
  tween(cam,duration,{FieldOfView=self.BaseFOV-8-rank},Enum.EasingStyle.Quad,Enum.EasingDirection.In)
  self:BlurTo(rank>=6 and 10 or 6,duration)
 end
 local vp=self.Root.RollReel.Reveal.Viewport local beat=scaleFor(vp,"Heartbeat")
 local steps=math.floor(duration/.16)
 for i=1,steps do
  task.delay(i*duration/steps*.95,function()
   if self.Destroyed then return end
   beat.Scale=1.07 tween(beat,.12,{Scale=1})
   self:Sound("Tick",.8+i/steps*.9,.4)
   if i%2==0 then self:EdgeGlow(color,math.min(rank,4),.25) end
  end)
 end
 self:Sound("Whoosh",.6,.4)
 task.delay(duration,function() tween(dim,.35,{BackgroundTransparency=1}) Debris:AddItem(dim,.4) self:BlurTo(0,.3) end)
end
function VFX:Banner(text,color,scale,position,hold,rainbow)
 local l=Instance.new("TextLabel") l.Name="Banner" l.BackgroundTransparency=1 l.AnchorPoint=Vector2.new(.5,.5)
 l.Position=position or UDim2.fromScale(.5,.3) l.Size=UDim2.fromOffset(900,150) l.Text=text l.TextScaled=true
 l.FontFace=Font.new("rbxasset://fonts/families/FredokaOne.json") l.TextColor3=Color3.new(1,1,1) l.ZIndex=120 l.Active=false l.Parent=self.Layer
 local st=Instance.new("UIStroke") st.Thickness=6 st.Color=color:Lerp(Color3.new(0,0,0),.55) st.Parent=l
 local g=Instance.new("UIGradient") g.Rotation=90
 g.Color=rainbow and ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,80,80)),ColorSequenceKeypoint.new(.25,Color3.fromRGB(255,220,60)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(80,255,140)),ColorSequenceKeypoint.new(.75,Color3.fromRGB(70,190,255)),ColorSequenceKeypoint.new(1,Color3.fromRGB(200,90,255))})
  or ColorSequence.new(Color3.new(1,1,1),color) g.Parent=l
 local sc=scaleFor(l,"Pop") sc.Scale=.2
 l.Rotation=-8 tween(sc,.45,{Scale=scale or 1},Enum.EasingStyle.Back) tween(l,.45,{Rotation=0},Enum.EasingStyle.Back)
 if rainbow then task.spawn(function() local t0=os.clock() while l.Parent do g.Offset=Vector2.new(0,math.sin((os.clock()-t0)*4)*.4) g.Rotation=90+(os.clock()-t0)*120 task.wait() end end) end
 task.delay(hold or 1.2,function() if l.Parent then tween(sc,.25,{Scale=(scale or 1)*1.15}) tween(l,.25,{TextTransparency=1}) tween(st,.25,{Transparency=1}) Debris:AddItem(l,.3) end end)
 return l
end
function VFX:Shockwave(point,color,count)
 for k=1,count or 1 do
  task.delay((k-1)*.12,function()
   if self.Destroyed then return end
   local r=image(self.Layer,"Shockwave",IMG.Ring,UDim2.fromOffset(40,40),UDim2.fromOffset(point.X,point.Y),2)
   r.ImageColor3=color r.ImageTransparency=.05
   tween(r,.6,{Size=UDim2.fromOffset(900,900),ImageTransparency=1},Enum.EasingStyle.Quart) Debris:AddItem(r,.65)
  end)
 end
end
function VFX:Rays(point,color,rank)
 if self.Quality=="Low" then return end
 local n=rank>=5 and 12 or 8
 local holder=Instance.new("Frame") holder.Name="Rays" holder.BackgroundTransparency=1 holder.Size=UDim2.fromScale(1,1) holder.Active=false holder.ZIndex=56 holder.Parent=self.Root
 local life=1.4+rank*.25
 for i=1,n do
  local ray=Instance.new("Frame") ray.BorderSizePixel=0 ray.AnchorPoint=Vector2.new(.5,.5) ray.Position=UDim2.fromOffset(point.X,point.Y)
  ray.Size=UDim2.fromOffset(1500,rank>=5 and 70 or 46) ray.BackgroundColor3=rank>=6 and Color3.fromHSV(i/n,.6,1) or color ray.BackgroundTransparency=1 ray.ZIndex=56 ray.Parent=holder
  local g=Instance.new("UIGradient") g.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.45,.35),NumberSequenceKeypoint.new(.5,.1),NumberSequenceKeypoint.new(.55,.35),NumberSequenceKeypoint.new(1,1)}) g.Parent=ray
  ray.Rotation=i/n*180
  tween(ray,.3,{BackgroundTransparency=.45})
  tween(ray,life,{Rotation=ray.Rotation+(rank>=5 and 70 or 40)},Enum.EasingStyle.Linear)
  task.delay(life-.4,function() if ray.Parent then tween(ray,.4,{BackgroundTransparency=1}) end end)
 end
 Debris:AddItem(holder,life+.1)
end
function VFX:EdgeGlow(color,rank,dur)
 if self.Quality=="Low" and not dur then return end
 dur=dur or (.6+rank*.15)
 for _,side in {{UDim2.new(0,0,0,0),UDim2.new(1,0,0,170),90},{UDim2.new(0,0,1,-170),UDim2.new(1,0,0,170),-90},{UDim2.new(0,0,0,0),UDim2.new(0,220,1,0),0},{UDim2.new(1,-220,0,0),UDim2.new(0,220,1,0),180}} do
  local f=Instance.new("Frame") f.Name="EdgeGlow" f.BorderSizePixel=0 f.BackgroundColor3=color f.Position=side[1] f.Size=side[2] f.BackgroundTransparency=1 f.ZIndex=57 f.Active=false f.Parent=self.Root
  local g=Instance.new("UIGradient") g.Rotation=side[3] g.Transparency=NumberSequence.new(0,1) g.Parent=f
  tween(f,dur*.3,{BackgroundTransparency=.35}) task.delay(dur*.3,function() if f.Parent then tween(f,dur*.7,{BackgroundTransparency=1}) end end) Debris:AddItem(f,dur+.05)
 end
end
function VFX:ScreenFlash(color,strength)
 local f=Instance.new("Frame") f.Name="ScreenFlash" f.BorderSizePixel=0 f.BackgroundColor3=color f.Size=UDim2.fromScale(1,1) f.BackgroundTransparency=strength or .3 f.ZIndex=58 f.Active=false f.Parent=self.Root
 tween(f,.45,{BackgroundTransparency=1}) Debris:AddItem(f,.5)
end
function VFX:StarRain(color,count,rainbow)
 local w=self.Root.AbsoluteSize.X/self.Root.Scale.Scale
 for i=1,count do
  task.delay(math.random()*.8,function()
   if self.Destroyed or self.UIAlive>90 then return end
   self.UIAlive+=1
   local s=image(self.Layer,"Star",IMG.Glow,UDim2.fromOffset(18,18),UDim2.fromOffset(math.random()*w,-30),3)
   s.ImageColor3=rainbow and Color3.fromHSV(math.random(),.6,1) or (i%3==0 and Color3.new(1,1,1) or color)
   local t=1.1+math.random()*.8
   tween(s,t,{Position=s.Position+UDim2.fromOffset((math.random()-.5)*160,900),Rotation=math.random(-200,200),ImageTransparency=.6},Enum.EasingStyle.Sine)
   task.delay(t,function() s:Destroy() self.UIAlive=math.max(0,self.UIAlive-1) end)
  end)
 end
end
function VFX:Glitch(duration)
 if self.Quality=="Low" then return end
 local area=self.Root.RollReel.Reveal local base=area.Position local t0=os.clock()
 task.spawn(function()
  while os.clock()-t0<duration and not self.Destroyed do
   area.Position=base+UDim2.fromOffset(math.random(-14,14),math.random(-6,6))
   task.wait(.04)
  end
  area.Position=base
 end)
end
-- beam of light over the local player's plot for big pulls
function VFX:LightPillar(color,rank)
 local char=Players.LocalPlayer.Character local rp=char and char:FindFirstChild("HumanoidRootPart") if not rp then return end
 local pos=rp.Position-Vector3.new(0,3,0)
 local beam=Instance.new("Part") beam.Name="RarePillar" beam.Anchored=true beam.CanCollide=false beam.CanQuery=false beam.CanTouch=false beam.CastShadow=false
 beam.Material=Enum.Material.Neon beam.Color=color beam.Shape=Enum.PartType.Cylinder beam.Transparency=.35
 beam.Size=Vector3.new(160,3,3) beam.CFrame=CFrame.new(pos+Vector3.new(0,80,0))*CFrame.Angles(0,0,math.pi/2) beam.Parent=self.World
 tween(beam,.35,{Size=Vector3.new(160,7+rank,7+rank)},Enum.EasingStyle.Back)
 task.delay(1.2+rank*.2,function() if beam.Parent then tween(beam,.6,{Size=Vector3.new(160,.2,.2),Transparency=1}) end end)
 Debris:AddItem(beam,2.4+rank*.2)
 self:WorldBurst(pos,color,self:Q(24+rank*6),"Rare")
end
-- extra show when an expensive dice is used (vfx level 1..5 from GameData)
function VFX:DiceRoll(d)
 local lvl=d.vfx or 0 if lvl<=0 or self.Destroyed then return end
 local c=d.color=="rainbow" and Color3.fromHSV(math.random(),.7,1) or Color3.fromHex(d.color)
 local btn=self.Root.HUD.RollArea.RollButton local point=self:Point(btn)
 self:UIBurst(point,c,self:Q(8+lvl*5),120+lvl*30)
 self:Shockwave(point,c,math.min(lvl,3))
 if lvl>=2 then self:EdgeGlow(c,lvl) end
 if lvl>=3 then self:Banner(string.upper(d.name).."!",c,.8+lvl*.08,UDim2.new(.5,0,.5,-420),1.1,lvl>=5) self:Sound("Boost",.9,.45) end
 if lvl>=4 then self:ScreenFlash(c,.55) self:StarRain(c,self:Q(lvl*6),d.color=="rainbow" or lvl>=5) end
 if lvl>=5 then self.ShakeUntil=os.clock()+.35 self.ShakeStrength=.08 end
end
function VFX:Potion(p)
 self:Sound("Potion")
 local c=p.color=="rainbow" and Color3.fromHSV(math.random(),.7,1) or Color3.fromHex(p.color)
 local char=Players.LocalPlayer.Character local rp=char and char:FindFirstChild("HumanoidRootPart")
 if rp then self:WorldBurst(rp.Position-Vector3.new(0,2.5,0),c,self:Q(26),"Teleport") end
 local holder=self.Root.HUD:FindFirstChild("ActivePotions")
 local point=holder and self:Point(holder) or self:Point(self.Root.HUD.CashPanel)
 self:UIBurst(point,c,self:Q(16),160) self:Shockwave(point,c,1)
end
-- ------------------------------------------------------------------ camera + screen effects
function VFX:CamFX()
 local cam=workspace.CurrentCamera if not cam then return nil end
 if not self.Blur or self.Blur.Parent~=cam then
  self.Blur=Instance.new("BlurEffect") self.Blur.Name="VFXBlur" self.Blur.Size=0 self.Blur.Parent=cam
  self.Grade=Instance.new("ColorCorrectionEffect") self.Grade.Name="VFXGrade" self.Grade.Parent=cam
 end
 return cam
end
-- quick zoom-in-and-back kick of the camera field of view
function VFX:CameraPunch(amount,dur)
 local cam=self:CamFX() if not cam then return end
 self.BaseFOV=self.BaseFOV or cam.FieldOfView
 cam.FieldOfView=self.BaseFOV-amount
 tween(cam,dur or .5,{FieldOfView=self.BaseFOV},Enum.EasingStyle.Back)
end
function VFX:BlurTo(size,dur) if not self:CamFX() then return end tween(self.Blur,dur or .25,{Size=size}) end
function VFX:Tint(color,dur,strength)
 if not self:CamFX() then return end
 local g=self.Grade g.TintColor=Color3.new(1,1,1):Lerp(color,strength or .45) g.Brightness=.12 g.Saturation=.35
 tween(g,dur or .6,{TintColor=Color3.new(1,1,1),Brightness=0,Saturation=0})
end
-- anime speed lines rushing towards the centre of the screen
function VFX:SpeedLines(dur,color)
 if self.Quality=="Low" then return end
 local holder=Instance.new("Frame") holder.Name="SpeedLines" holder.BackgroundTransparency=1 holder.Size=UDim2.fromScale(1,1) holder.ZIndex=54 holder.Active=false holder.Parent=self.Root
 local size=self.Root.AbsoluteSize/self.Root.Scale.Scale local c=Vector2.new(size.X/2,size.Y*.46)
 local t0=os.clock()
 task.spawn(function()
  while os.clock()-t0<dur and holder.Parent and not self.Destroyed do
   for _=1,3 do
    local a=math.random()*math.pi*2 local r=math.max(size.X,size.Y)*.62
    local len=math.random(160,320)
    local l=Instance.new("Frame") l.BorderSizePixel=0 l.AnchorPoint=Vector2.new(.5,.5) l.BackgroundColor3=math.random()<.25 and color or Color3.new(1,1,1)
    l.BackgroundTransparency=.25 l.Size=UDim2.fromOffset(len,math.random(3,7)) l.Rotation=math.deg(a) l.ZIndex=54
    l.Position=UDim2.fromOffset(c.X+math.cos(a)*r,c.Y+math.sin(a)*r) l.Parent=holder
    local g=Instance.new("UIGradient") g.Transparency=NumberSequence.new(0,1) g.Rotation=180 g.Parent=l
    tween(l,.32,{Position=UDim2.fromOffset(c.X+math.cos(a)*r*.38,c.Y+math.sin(a)*r*.38),BackgroundTransparency=1},Enum.EasingStyle.Quad)
    Debris:AddItem(l,.35)
   end
   task.wait(.03)
  end
  Debris:AddItem(holder,.4)
 end)
end
-- red/cyan split copies of a label for a glitchy "impossible pull" look
function VFX:Chromatic(label,dur)
 if self.Quality=="Low" or not label.Parent then return end
 for i,c in {Color3.fromRGB(255,40,80),Color3.fromRGB(40,220,255)} do
  local copy=label:Clone() copy.Name="Chroma" copy.ZIndex=label.ZIndex-1 copy.TextColor3=c
  for _,d in copy:GetChildren() do if not d:IsA("UIScale") then d:Destroy() end end
  copy.TextTransparency=.35 copy.Parent=label.Parent
  task.spawn(function()
   local t0=os.clock()
   while os.clock()-t0<dur and copy.Parent and label.Parent do
    local k=(i==1 and -1 or 1)*(6+math.sin((os.clock()-t0)*30)*5)
    copy.Position=label.Position+UDim2.fromOffset(k,math.random(-2,2)) copy.Rotation=label.Rotation
    local s1,s2=copy:FindFirstChild("Pop"),label:FindFirstChild("Pop") if s1 and s2 then s1.Scale=s2.Scale end
    task.wait()
   end
   copy:Destroy()
  end)
 end
end
function VFX:Milestone(text)
 self:Sound("Milestone")
 self:Banner(text,Color3.fromRGB(255,214,64),.75,UDim2.new(.5,0,0,190),1.6)
 self:Confetti(self:Point(self.Root.HUD.CashPanel),Color3.fromRGB(255,214,64),self:Q(26),false)
end
function VFX:WorldBurst(pos,color,count,kind)
 local cam=workspace.CurrentCamera
 if self.Destroyed or not cam or (cam.CFrame.Position-pos).Magnitude>200 or self.WorldAlive>=28 then return end
 self.WorldAlive+=1 self.Metrics.worldBursts+=1 self.Gui:SetAttribute("VFXWorldBursts",self.Metrics.worldBursts)
 local anchor=Instance.new("Part") anchor.Name="Burst_"..(kind or "Spark") anchor.Anchored=true anchor.Transparency=1
 anchor.CanCollide=false anchor.CanQuery=false anchor.CanTouch=false anchor.Size=Vector3.one anchor.Position=pos+Vector3.new(0,.7,0) anchor.Parent=self.World
 local att=Instance.new("Attachment") att.Parent=anchor
 local e=Instance.new("ParticleEmitter") e.Texture=IMG.Glow e.Rate=0 e.Lifetime=NumberRange.new(.35,.65) e.Speed=NumberRange.new(3,9)
 e.SpreadAngle=Vector2.new(75,75) e.Rotation=NumberRange.new(0,360) e.RotSpeed=NumberRange.new(-100,100)
 e.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,.24),NumberSequenceKeypoint.new(.2,.42),NumberSequenceKeypoint.new(1,0)})
 e.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.12),NumberSequenceKeypoint.new(.6,.35),NumberSequenceKeypoint.new(1,1)})
 e.Color=ColorSequence.new(color,Color3.new(1,1,1)) e.LightEmission=.75 e.Acceleration=Vector3.new(0,-8,0) e.Drag=2 e.Parent=att e:Emit(count or 14)
 local light=Instance.new("PointLight") light.Color=color light.Range=12 light.Brightness=1.1 light.Shadows=false light.Parent=anchor tween(light,.38,{Brightness=0})
 -- Two expanding circular waves and rising motes form the teleport aura.
 -- The texture is a plain ring drawn for this effect; no currency logos.
 local teleport=kind=="Teleport"
 local diameter=kind=="Coin" and 4 or teleport and 12 or 9
 local ground=workspace:Raycast(pos+Vector3.new(0,3,0),Vector3.new(0,-9,0),self.GroundRayParams)
 local y=ground and ground.Position.Y+.09 or pos.Y+.09
 local function pulse(delay,destination)
  task.delay(delay,function()
   if self.Destroyed or not anchor.Parent then return end
   local ring=Instance.new("Part") ring.Name=teleport and "TeleportAuraRing" or "GroundRipple"
   ring.Anchored=true ring.CanCollide=false ring.CanQuery=false ring.CanTouch=false ring.Transparency=1
   ring.Size=Vector3.new(2,.035,2) ring.CFrame=CFrame.new(pos.X,y,pos.Z) ring.Parent=self.World
   local surface=Instance.new("SurfaceGui") surface.Face=Enum.NormalId.Top surface.CanvasSize=Vector2.new(256,256) surface.LightInfluence=0 surface.Parent=ring
   local glow=image(surface,"CircleWave",IMG.Ring,UDim2.fromScale(1,1),UDim2.fromScale(.5,.5),1)
   glow.ImageColor3=color glow.ImageTransparency=teleport and .18 or .35
   tween(ring,.65,{Size=Vector3.new(destination,.035,destination)},Enum.EasingStyle.Quart)
   tween(glow,.65,{ImageTransparency=1}) Debris:AddItem(ring,.7)
  end)
 end
 pulse(0,diameter)
 if teleport then
  self.Gui:SetAttribute("VFXTeleportAuraCount",(self.Gui:GetAttribute("VFXTeleportAuraCount") or 0)+1)
  pulse(.14,diameter*.78)
  e.Speed=NumberRange.new(1.5,4) e.Acceleration=Vector3.new(0,5,0)
  e.Lifetime=NumberRange.new(.45,.85) e.Drag=1.5
  -- Six columns of small light particles rise around the avatar.
  for i=1,6 do
   local a=Instance.new("Attachment") local angle=i/6*math.pi*2
   a.Position=Vector3.new(math.cos(angle)*2.1,.1,math.sin(angle)*2.1) a.Parent=anchor
   local mote=e:Clone() mote.SpreadAngle=Vector2.new(12,12)
   mote.Speed=NumberRange.new(3,6) mote.EmissionDirection=Enum.NormalId.Top mote.Parent=a mote:Emit(4)
  end
 end
 task.delay(1,function() anchor:Destroy() self.WorldAlive=math.max(0,self.WorldAlive-1) end)
end
function VFX:Place(pos,model)
 self.Metrics.placements+=1 self.Gui:SetAttribute("VFXPlacements",self.Metrics.placements) self:WorldBurst(pos,Color3.fromRGB(99,255,170),20,"Build") self:Sound("Place",.96+math.random()*.08)
 if not model or not model.Parent then return end
 local h=Instance.new("Highlight") h.Name="PlacementFlash" h.Adornee=model h.FillColor=Color3.fromRGB(130,255,197)
 h.OutlineColor=Color3.new(1,1,1) h.FillTransparency=.55 h.OutlineTransparency=.18 h.DepthMode=Enum.HighlightDepthMode.Occluded h.Parent=model
 tween(h,.55,{FillTransparency=1,OutlineTransparency=1}) Debris:AddItem(h,.6)
 local copy=model:Clone() copy.Name="PlacementPop"
 local parts={}
 for _,p in model:GetDescendants() do if p:IsA("BasePart") then parts[#parts+1]={p,p.LocalTransparencyModifier} p.LocalTransparencyModifier=1 end end
 for _,p in copy:GetDescendants() do if p:IsA("BasePart") then p.CanCollide=false p.CanQuery=false p.CanTouch=false p.Anchored=true p.LocalTransparencyModifier=0 elseif p:IsA("Highlight") or p:IsA("LuaSourceContainer") then p:Destroy() end end
 copy.Parent=self.World
 local pivot=copy:GetPivot() local size=copy:GetScale() local value=Instance.new("NumberValue") value.Value=.86
 local connection=value.Changed:Connect(function(v) if copy.Parent then copy:ScaleTo(size*v) copy:PivotTo(pivot) end end)
 copy:ScaleTo(size*.86) copy:PivotTo(pivot*CFrame.new(0,2.5,0))
 connection:Disconnect()
 connection=value.Changed:Connect(function(v) if copy.Parent then copy:ScaleTo(size*v) copy:PivotTo(pivot*CFrame.new(0,(1-v)/.14*2.5,0)) end end)
 tween(value,.3,{Value=1},Enum.EasingStyle.Bounce)
 local id=model:GetAttribute("PieceId")
 local stats=require(game:GetService("ReplicatedStorage").Shared.Stats)
 local piece=id and stats.Pieces[id]
 local rank=piece and RANK[piece.tier] or 1
 if rank>=3 then
  local c=COLORS[piece.tier]
  task.delay(.25,function() self:WorldBurst(pos,c,self:Q(16+rank*4),"Rare") if rank>=4 then self:Sound("Unlock",1.15,.3) end end)
 end
 task.delay(.32,function()
  connection:Disconnect() value:Destroy() copy:Destroy()
  for _,entry in parts do if entry[1].Parent then entry[1].LocalTransparencyModifier=entry[2] end end
 end)
end
function VFX:Remove(pos)
 self:WorldBurst(pos,Color3.fromRGB(255,109,139),14,"Remove") self:Sound("Remove")
end
function VFX:Earn(amount,pos)
 if amount<=0 then return end
 local now=os.clock() if now-(self.LastEarn or -100)<.22 then return end self.LastEarn=now
 self:WorldBurst(pos,Color3.fromRGB(255,219,78),5,"Coin") self:Sound("Coin",.95+math.random()*.13,.23)
 local camera=workspace.CurrentCamera if not camera then return end local point,visible=camera:WorldToViewportPoint(pos+Vector3.new(0,2,0))
 if not visible or not self.Root.HUD.Visible then return end
 local start=Vector2.new(point.X,point.Y)/self.Root.Scale.Scale local target=self:Point(self.Root.HUD.CashPanel)
 local label=Instance.new("TextLabel") label.Name="CoinFly" label.BackgroundTransparency=1 label.AnchorPoint=Vector2.new(.5,.5)
 label.Text="$" label.FontFace=Font.new("rbxasset://fonts/families/FredokaOne.json") label.TextSize=29 label.TextColor3=Color3.fromRGB(255,221,60)
 label.Size=UDim2.fromOffset(36,36) label.Position=UDim2.fromOffset(start.X,start.Y) label.ZIndex=101 label.Parent=self.Layer
 local stroke=Instance.new("UIStroke") stroke.Color=Color3.fromRGB(81,55,16) stroke.Thickness=2 stroke.Parent=label
 tween(label,.42,{Position=UDim2.fromOffset(target.X,target.Y),Rotation=20,TextTransparency=.2},Enum.EasingStyle.Quart)
 task.delay(.42,function()
  label:Destroy() local s=scaleFor(self.Root.HUD.CashPanel,"IncomePop") s.Scale=1.025 tween(s,.18,{Scale=1})
 end)
end
function VFX:Purchase(kind)
 self.Metrics.purchases+=1 self:Sound(kind=="Upgrade" and "Unlock" or "Purchase")
 local point=self:Point(self.Root.HUD.CashPanel)
 for _,w in self.Root.Windows:GetChildren() do if w:IsA("GuiObject") and w.Visible then point=self:Point(w) break end end
 if self.LastButton and self.LastButton.Parent then point=self:Point(self.LastButton) self:Ripple(self.LastButton,Color3.fromRGB(135,255,112)) end
 self:UIBurst(point,Color3.fromRGB(135,255,112),18,180)
 local character=Players.LocalPlayer.Character local rp=character and character:FindFirstChild("HumanoidRootPart")
 if rp then self:WorldBurst(rp.Position-Vector3.new(0,3,0),Color3.fromRGB(137,255,123),12,"Purchase") end
end
function VFX:Error(button)
 self:Sound("Error")
 if button and button.Parent then
  local pos=button.Position tween(button,.06,{Position=pos+UDim2.fromOffset(5,0)})
  task.delay(.06,function() if button.Parent then tween(button,.08,{Position=pos-UDim2.fromOffset(4,0)}) end end)
  task.delay(.14,function() if button.Parent then tween(button,.10,{Position=pos}) end end)
 end
end
function VFX:Toast(frame)
 local s=scaleFor(frame,"ToastPop") s.Scale=.6 tween(s,.32,{Scale=1},Enum.EasingStyle.Back)
 frame.Rotation=-4 tween(frame,.4,{Rotation=0},Enum.EasingStyle.Elastic)
end
function VFX:Window(window)
 if window.Name=="BuildPanel" then
  -- slide up from below with a little bounce
  self:Sound("BuildOpen")
  local target=window.Position
  window.Position=target+UDim2.fromOffset(0,140)
  tween(window,.32,{Position=target},Enum.EasingStyle.Back)
  local pop=scaleFor(window,"Pop") pop.Scale=.96 tween(pop,.3,{Scale=1},Enum.EasingStyle.Back)
  local n=0
  for _,d in window.Items:GetChildren() do
   if d:IsA("GuiObject") and d.Visible then
    n+=1 local p=scaleFor(d,"Entrance") p.Scale=.7
    task.delay(math.min(n*.025,.25),function() if d.Parent then tween(p,.25,{Scale=1},Enum.EasingStyle.Back) end end)
   end
  end
  return
 end
 self:Sound("Whoosh",1.15,.25)
 if window.Name=="SkillsWindow" then
  self:UIBurst(self:Point(window.Header.Icon),Color3.fromRGB(208,133,255),8,75)
  return
 end
 local pop=scaleFor(window,"Pop") pop.Scale=.93 tween(pop,.28,{Scale=1},Enum.EasingStyle.Back)
 local n=0
 for _,d in window:GetDescendants() do
  if d:IsA("GuiObject") and (d.Name:match("^Piece_") or d.Name:match("^Car_") or d.Name:match("^Potion_") or d.Name:match("^Dice_")) and d.Visible then
   n+=1 local p=scaleFor(d,"Entrance") p.Scale=.94
   task.delay(math.min(n*.016,.14),function() if d.Parent then tween(p,.28,{Scale=1},Enum.EasingStyle.Back) end end)
  end
 end
end
function VFX:WatchCard(card)
 local glow=card:FindFirstChild("Glow") if not glow then return end
 self:Connect(card.MouseEnter,function()
  tween(glow,.2,{Size=UDim2.fromScale(.98,.80)})
  local vp=card:FindFirstChild("ModelPreview") if vp and vp.CurrentCamera then tween(vp.CurrentCamera,.2,{FieldOfView=37}) end
 end)
 self:Connect(card.MouseLeave,function()
  tween(glow,.2,{Size=UDim2.fromScale(.93,.72)})
  local vp=card:FindFirstChild("ModelPreview") if vp and vp.CurrentCamera then tween(vp.CurrentCamera,.2,{FieldOfView=40}) end
 end)
end
function VFX:AttachCar(car)
 if self.Cars[car] then return end local rp=car:FindFirstChild("Root") if not rp then return end
 local state={root=rp,position=rp.Position,trails={},dust=nil,lastBoost=-100}
 self.Cars[car]=state
 for _,side in {-1,1} do
  local a=Instance.new("Attachment") a.Name="SpeedTrailTop" a.Position=Vector3.new(side*1.35,.38,1.5) a.Parent=rp
  local b=Instance.new("Attachment") b.Name="SpeedTrailBottom" b.Position=Vector3.new(side*1.35,.1,1.5) b.Parent=rp
  local t=Instance.new("Trail") t.Name="SpeedTrail" t.Attachment0=a t.Attachment1=b t.Color=ColorSequence.new(Color3.fromRGB(139,232,255),Color3.fromRGB(41,147,255))
  t.Lifetime=.27 t.LightEmission=.75 t.FaceCamera=true t.MinLength=.08 t.Transparency=NumberSequence.new(.55,1) t.WidthScale=NumberSequence.new(.55,0) t.Enabled=false t.Parent=rp
  state.trails[#state.trails+1]=t
 end
 local att=Instance.new("Attachment") att.Name="TireDust" att.Position=Vector3.new(0,-.25,1.3) att.Parent=rp
 local e=Instance.new("ParticleEmitter") e.Name="TireDust" e.Texture="rbxasset://textures/particles/smoke_main.dds" e.Rate=0 e.Lifetime=NumberRange.new(.2,.35)
 e.Speed=NumberRange.new(.4,1.2) e.SpreadAngle=Vector2.new(20,20) e.EmissionDirection=Enum.NormalId.Back
 e.Size=NumberSequence.new(.22,.65) e.Transparency=NumberSequence.new(.78,1) e.Color=ColorSequence.new(Color3.fromRGB(212,225,226)) e.Parent=att state.dust=e
end
function VFX:DecorateTrack(model)
 if not model:IsA("Model") or model:GetAttribute("LocalAura") then return end
 local id=model:GetAttribute("PieceId")
 local stats=require(game:GetService("ReplicatedStorage").Shared.Stats)
 local piece=id and stats.Pieces[id]
 if not piece or ((RANK[piece.tier] or 1)<3 and id~="BoostPad") then return end
 model:SetAttribute("LocalAura",true)
 local cf,size=model:GetBoundingBox() local color=COLORS[piece.tier] or COLORS.Rare
 if id=="BoostPad" then self.BoostZones[model]={cf,size} end
 local anchor=Instance.new("Part") anchor.Name="TrackAura" anchor.Transparency=1 anchor.Anchored=true anchor.CanCollide=false anchor.CanQuery=false anchor.CanTouch=false
 anchor.Size=Vector3.new(math.min(8,size.X*.5),.1,math.min(8,size.Z*.5)) anchor.Position=cf.Position+Vector3.new(0,.25,0) anchor.Parent=self.World
 local e=Instance.new("ParticleEmitter") e.Name="RaritySparkles" e.Texture=IMG.Glow e.Color=ColorSequence.new(color,Color3.new(1,1,1))
 e.Rate=id=="BoostPad" and 5 or 2 e.Lifetime=NumberRange.new(.45,.8) e.Speed=NumberRange.new(.5,1.5) e.LightEmission=.65
 e.Size=NumberSequence.new(.18,0) e.Transparency=NumberSequence.new(.15,1) e.SpreadAngle=Vector2.new(8,8) e.Rotation=NumberRange.new(0,360) e.Parent=anchor
 self.AmbientEmitters[#self.AmbientEmitters+1]={anchor,e}
 self:Connect(model.Destroying,function() self.BoostZones[model]=nil anchor:Destroy() end)
end
function VFX:Ambient()
 local map=workspace:FindFirstChild("Map") if not map then return end
 local hub=map:FindFirstChild("Hub")
 if hub then
  for _,m in hub:GetChildren() do
   if m:IsA("Model") and m.Name=="Landmark" then
    local cf,size=m:GetBoundingBox() size=Vector3.new(size.X,4,size.Z) cf=cf-Vector3.new(0,cf.Y-(hub.Ground.Position.Y+9.4),0) local anchor=Instance.new("Part") anchor.Name="FountainSpray" anchor.Anchored=true anchor.CanCollide=false anchor.CanQuery=false anchor.Transparency=1
    anchor.Size=Vector3.one anchor.Position=Vector3.new(cf.X,cf.Y+size.Y*.20,cf.Z) anchor.Parent=self.World
    local att=Instance.new("Attachment") att.Parent=anchor
    local e=Instance.new("ParticleEmitter") e.Name="WaterDroplets" e.Texture=IMG.Glow e.Rate=16 e.Lifetime=NumberRange.new(.5,.75) e.Speed=NumberRange.new(4,6)
    e.Acceleration=Vector3.new(0,-15,0) e.SpreadAngle=Vector2.new(18,18) e.Size=NumberSequence.new(.13,.045) e.Color=ColorSequence.new(Color3.fromRGB(96,220,255),Color3.new(1,1,1)) e.Transparency=NumberSequence.new(.2,1) e.LightEmission=.45 e.Parent=att
    self.AmbientEmitters[#self.AmbientEmitters+1]={anchor,e}
   end
  end
 end
 local plots=map:FindFirstChild("Plots") if not plots then return end
 for _,plot in plots:GetChildren() do
  local track=plot:FindFirstChild("Track")
  if track then
   for _,model in track:GetChildren() do self:DecorateTrack(model) end
   self:Connect(track.ChildAdded,function(model)
    task.delay(.06,function()
     if not model.Parent or not model:IsA("Model") then return end
     self:DecorateTrack(model)
     if os.clock()-self.Started>1.5 and plot:GetAttribute("OwnerId")==Players.LocalPlayer.UserId and model:GetAttribute("PieceId")~="Start" then local cf=model:GetBoundingBox() self:Place(cf.Position,model) end
    end)
   end)
  end
  self:Connect(plot.ChildAdded,function(o) if o.Name=="Car" and o:IsA("Model") then task.defer(function() self:AttachCar(o) end) end end)
  local car=plot:FindFirstChild("Car") if car then self:AttachCar(car) end
 end
end
function VFX.new(gui)
 local self=setmetatable({Gui=gui,Root=gui.Root,Connections={},Voices={},LastSound={},Cars={},BoostZones={},AmbientEmitters={},UIAlive=0,WorldAlive=0,Started=os.clock(),Metrics={sounds=0,uiBursts=0,worldBursts=0,rollStarts=0,results=0,placements=0,purchases=0}},VFX)
 VFX.Active=self
 -- A Folder cannot obscure GUI hit-testing the way a full-screen effects Frame can.
 local layer=Instance.new("Folder") layer.Name="VFXOverlay" layer.Parent=self.Root self.Layer=layer
 local world=Instance.new("Folder") world.Name="LocalPresentationVFX" world.Parent=workspace self.World=world
 local group=Instance.new("SoundGroup") group.Name="TrackRNGSFX" group.Volume=.8 group.Parent=SoundService self.SoundGroup=group
 local mgroup=Instance.new("SoundGroup") mgroup.Name="TrackRNGMusic" mgroup.Volume=0 mgroup.Parent=SoundService self.MusicGroup=mgroup
 self.Pools={} self.SfxOn=true self.MusicOn=true self.Quality="High"
 if AUDIO.music then
  local m=Instance.new("Sound") m.Name="TrackRNGMusic" m.SoundId=AUDIO.music m.Looped=true m.Volume=1 m.SoundGroup=mgroup m.Parent=SoundService self.Music=m
  task.delay(1.5,function() if not self.Destroyed and self.MusicOn then m:Play() tween(mgroup,3,{Volume=.32}) end end)
 end
 task.spawn(function() pcall(function() ContentProvider:PreloadAsync({IMG.Glow,IMG.Ring}) end) end)
 local params=RaycastParams.new() params.FilterType=Enum.RaycastFilterType.Exclude
 params.FilterDescendantsInstances={world,Players.LocalPlayer.Character}
 self.GroundRayParams=params
 for _,p in gui:GetDescendants() do
  if p:IsA("GuiObject") and p.Name=="Halftone" then p:Destroy()
  elseif p:IsA("GuiObject") and p.Name:match("^Piece_") then self:WatchCard(p) end
 end
 local function anyOpen() for _,w in self.Root.Windows:GetChildren() do if w:IsA("GuiObject") and w.Visible and w.Name~="SkillsWindow" then return true end end return false end
 for _,window in self.Root.Windows:GetChildren() do if window:IsA("GuiObject") then self:Connect(window:GetPropertyChangedSignal("Visible"),function()
  if window.Visible then self:Window(window) else self:Sound("WindowClose") end
  -- soft background blur while a menu is open
  self:BlurTo(anyOpen() and (self.Quality=="Low" and 0 or 9) or 0,.25)
 end) end end
 self:Connect(self.Root.BuildPanel:GetPropertyChangedSignal("Visible"),function() if self.Root.BuildPanel.Visible then self:Window(self.Root.BuildPanel) end end)
 for _,node in self.Root.Windows.SkillsWindow.Body.Tree:GetChildren() do if node:IsA("GuiButton") then self:Connect(node:GetPropertyChangedSignal("Visible"),function()
  if node.Visible and os.clock()-self.Started>1.5 and self.Root.Windows.SkillsWindow.Visible then local s=scaleFor(node,"Bounce") s.Scale=.8 tween(s,.35,{Scale=1},Enum.EasingStyle.Back) self:UIBurst(self:Point(node),Color3.fromRGB(127,255,109),6,65) end
 end) end end
 local die=self.Root.HUD.RollArea.RollButton.Die:FindFirstChild("AtlasImage")
 local dieScale=die and scaleFor(die,"IdlePulse")
 local badge=self.Root.HUD.RollArea.SkillsButton.Badge local badgeScale=scaleFor(badge,"NotificationPulse")
 local roll=self.Root.HUD.RollArea.RollButton
 local shine=Instance.new("UIGradient") shine.Name="IdleShine"
 shine.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,0),NumberSequenceKeypoint.new(.42,0),NumberSequenceKeypoint.new(.5,.6),NumberSequenceKeypoint.new(.58,0),NumberSequenceKeypoint.new(1,0)})
 shine.Rotation=25 shine.Offset=Vector2.new(-1,0)
 if not roll:FindFirstChildOfClass("UIGradient") then shine.Parent=roll end
 local menuScales={}
 for i,b in self.Root.HUD.LeftMenu:GetChildren() do if b:IsA("GuiButton") then menuScales[#menuScales+1]={scaleFor(b,"IdleBob"),i} end end
 self:Connect(RunService.RenderStepped,function()
  if self.Destroyed then return end local now=os.clock()
  if shine.Parent then shine.Offset=Vector2.new(((now*.45)%2.2)-1.1,0) end
  for _,m in menuScales do m[1].Scale=1+math.sin(now*2+m[2]*.9)*.018 end
  if die and self.Root.HUD.Visible then die.Rotation=math.sin(now*1.5)*1.8 dieScale.Scale=1+math.sin(now*2.2)*.012 end
  badgeScale.Scale=(tonumber(badge.Text.Text) or 0)>0 and 1+math.sin(now*4)*.045 or 1
 end)
 local acc=0
 self:Connect(RunService.Heartbeat,function(dt)
  acc+=dt if acc<.1 then return end local elapsed=acc acc=0 local cam=workspace.CurrentCamera if not cam then return end
  for car,state in self.Cars do
   if not car.Parent or not state.root.Parent then self.Cars[car]=nil continue end
   local pos=state.root.Position local delta=(pos-state.position).Magnitude local speed=delta/elapsed state.position=pos
   local moving=speed>3 and delta<30 and (cam.CFrame.Position-pos).Magnitude<160
   for _,trail in state.trails do
    trail.Enabled=moving
    if delta>25 then trail:Clear() end
   end
   state.dust.Rate=moving and 7 or 0
   local onBoost=false
   for _,zone in self.BoostZones do
    local localPos=zone[1]:PointToObjectSpace(pos)
    if math.abs(localPos.X)<zone[2].X/2+1 and math.abs(localPos.Z)<zone[2].Z/2+1 and math.abs(localPos.Y)<5 then onBoost=true break end
   end
   if moving and onBoost and not state.onBoost and os.clock()-state.lastBoost>1.5 then
    state.lastBoost=os.clock() self:WorldBurst(pos,Color3.fromRGB(93,214,255),7,"Boost")
    if car.Parent:GetAttribute("OwnerId")==Players.LocalPlayer.UserId then self:Sound("Boost",1,.23) end
   end
   state.onBoost=onBoost
  end
  for i=#self.AmbientEmitters,1,-1 do
   local e=self.AmbientEmitters[i]
   if not e[1].Parent then table.remove(self.AmbientEmitters,i)
   else e[2].Enabled=(cam.CFrame.Position-e[1].Position).Magnitude<150 end
  end
  local char=Players.LocalPlayer.Character local rp=char and char:FindFirstChild("HumanoidRootPart")
  if rp then local pos=rp.Position
   if self.CharacterPos and (pos-self.CharacterPos).Magnitude>55 then self:WorldBurst(pos-Vector3.new(0,3,0),Color3.fromRGB(136,230,255),22,"Teleport") self:Sound("Teleport",1,.34) end self.CharacterPos=pos
  else self.CharacterPos=nil end
 end)
 RunService:BindToRenderStep("TrackRNGVFXCamera",Enum.RenderPriority.Camera.Value+1,function()
  if self.ShakeUntil and os.clock()<self.ShakeUntil then local cam=workspace.CurrentCamera
   if cam then local k=(self.ShakeUntil-os.clock())/.23 local a=os.clock()*77 cam.CFrame=cam.CFrame*CFrame.new(math.sin(a)*self.ShakeStrength*k,math.cos(a*1.3)*self.ShakeStrength*k,0) end
  end
 end)
 task.delay(.8,function() if not self.Destroyed then self:Ambient() end end)
 self:Connect(gui.Destroying,function() self:Destroy() end)
 return self
end
function VFX:Destroy()
 if self.Destroyed then return end self.Destroyed=true
 for _,c in self.Connections do c:Disconnect() end
 RunService:UnbindFromRenderStep("TrackRNGVFXCamera")
 for _,pool in self.Pools do for _,snd in pool do if typeof(snd)=="Instance" then snd:Destroy() end end end
 if self.Music then self.Music:Destroy() end
 self.MusicGroup:Destroy()
 self.SoundGroup:Destroy() self.Layer:Destroy() self.World:Destroy()
end
return VFX




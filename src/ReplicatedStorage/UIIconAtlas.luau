
local Atlas={}
local CELLS={["🛒"]=1,["📘"]=2,["📅"]=3,["🎟️"]=4,["🎫"]=4,["🎁"]=5,["🏠"]=6,["🗺️"]=6,["🔨"]=7,["🔧"]=7,["⏫"]=8,["🎨"]=9,["🍀"]=10,["💵"]=11,["💰"]=11,["🪙"]=11,["👥"]=12,["🎲"]=13,["📦"]=17,["🧱"]=17,["🧪"]=19,["🚗"]=23,["⚡"]=24}
-- dice and potions now use their own rendered icons (ItemIcon), not atlas cells
local DICE={}
local POTIONS={}
-- Individual silhouette bounds in the original 1536x1024 atlas.
local RECTS={
 [1]={26,52,230,221},
 [2]={292,54,211,213},
 [3]={540,54,199,215},
 [4]={774,63,236,197},
 [5]={1038,48,221,226},
 [6]={1292,68,219,206},
 [7]={29,290,218,212},
 [8]={265,294,253,205},
 [9]={540,301,208,202},
 [10]={789,289,207,215},
 [11]={1034,300,229,207},
 [12]={1291,298,221,205},
 [13]={42,523,199,214},
 [14]={291,523,200,214},
 [15]={540,523,201,214},
 [16]={789,523,202,214},
 [17]={1032,520,227,224},
 [18]={1292,520,219,222},
 [19]={51,742,177,240},
 [20]={301,742,173,240},
 [21]={544,743,172,239},
 [22]={798,743,173,239},
 [23]={1010,761,272,207},
 [24]={1322,750,169,228},
}
local function icon(parent,index,asset)
 local rect=RECTS[index] if not rect then return nil end
 local img=parent:FindFirstChild("AtlasImage")
 if not img then img=Instance.new("ImageLabel") img.Name="AtlasImage" img.BackgroundTransparency=1 img.Parent=parent end
 img:SetAttribute("AtlasIndex",index)
 img.AnchorPoint=Vector2.new(.5,.5) img.Position=UDim2.fromScale(.5,.5) img.Size=UDim2.fromScale(.84,.84)
 img.Image=asset
 -- Roblox imported the source texture at 1024 pixels wide.
 img.ImageRectOffset=Vector2.new(math.floor(rect[1]*2/3),math.floor(rect[2]*2/3))
 img.ImageRectSize=Vector2.new(math.ceil(rect[3]*2/3),math.ceil(rect[4]*2/3))
 img.ScaleType=Enum.ScaleType.Fit img.ZIndex=parent.ZIndex+1
 parent.ClipsDescendants=false
 return img
end
function Atlas.SetIcon(parent,value,asset)
 local idx=if typeof(value)=="number" then value else CELLS[value]
 if not idx or not asset or asset=="" then return end
 if parent:IsA("TextLabel") then
  parent.TextTransparency=1
  for _,s in parent:GetChildren() do if s:IsA("UIStroke") then s.Transparency=1 end end
 end
 return icon(parent,idx,asset)
end
function Atlas.Apply(gui)
 local asset=gui:GetAttribute("IconAtlas")
 if not asset or asset=="" then return false end
 if not string.match(asset,"^rbxassetid://%d+$") then return false end
 local root=gui.Root local hud=root.HUD
 for _,d in root:GetDescendants() do
  if d:IsA("TextLabel") and d.Name~="AtlasImage" then
   local idx=CELLS[d.Text]
   local p=d.Parent
   if p:FindFirstChild("ItemIcon") then continue end
   if p.Name=="StarterCard" and d.Name=="Icon" then idx=18 end
   if p.Name=="Day5" and d.Name=="Icon" then idx=14 end
   if p.Name=="Item4" and d.Name=="Icon" then idx=15 end
   if p.Name=="Bg" and d.Name=="Icon" then idx=POTIONS[string.sub(p.Parent.Name,8)] or idx end
   if d==hud.RollArea.SkillsButton.Icon then idx=8 end
   if idx and (d.Name=="Icon" or d.Name=="Coin" or d.Name=="LuckIcon" or d.Name=="RollIcon") then
    d.TextTransparency=1
    for _,s in d:GetChildren() do if s:IsA("UIStroke") then s.Transparency=1 end end
    icon(d,idx,asset)
   end
  end
 end
 local skillsAsset=gui:GetAttribute("SkillsIcon")
 if skillsAsset and string.match(skillsAsset,"^rbxassetid://%d+$") then
  for _,parent in {hud.RollArea.SkillsButton.Icon,root.Windows.SkillsWindow.Header.Icon} do
   parent.TextTransparency=1
   local img=parent:FindFirstChild("AtlasImage") or Instance.new("ImageLabel")
   img.Name="AtlasImage" img.BackgroundTransparency=1 img.AnchorPoint=Vector2.new(.5,.5)
   local main=parent==hud.RollArea.SkillsButton.Icon
   img.Position=UDim2.fromScale(.5,main and .58 or .5) img.Size=UDim2.fromScale(.84,main and .78 or .9)
   img.ScaleType=Enum.ScaleType.Fit img.Image=skillsAsset img.ImageColor3=Color3.new(1,1,1)
   img.ImageRectOffset=Vector2.new(149,126) img.ImageRectSize=Vector2.new(725,774)
   img.ZIndex=parent.ZIndex+1 img.Parent=parent
  end
 end
 for _,name in {"ArrowL","ArrowR","ArrowC"} do hud.RollArea.SkillsButton[name].Visible=false end
 local die=hud.RollArea.RollButton.Die
 die.BackgroundTransparency=1
 for _,d in die:GetChildren() do
  if d:IsA("UIStroke") then d.Transparency=1 elseif d:IsA("Frame") and string.sub(d.Name,1,3)=="Pip" then d.Visible=false end
 end
 die.Rotation=0 die.Size=UDim2.fromOffset(216,190)
 local dieImage=icon(die,13,asset) dieImage.ZIndex=die.ZIndex+1
 die.Cooldown.ZIndex=die.ZIndex+2
 for name,idx in DICE do
  local chip=hud.RollArea.DiceBar:FindFirstChild("Dice_"..name)
  if chip then
   chip.BackgroundTransparency=1
   for _,s in chip:GetChildren() do if s:IsA("UIStroke") then s.Transparency=1 elseif s:IsA("UIGradient") then s.Enabled=false end end
   icon(chip,idx,asset).ZIndex=chip.ZIndex+1
   chip.Count.ZIndex=chip.ZIndex+2
  end
  local card=root.Windows.DiceShopWindow.Body:FindFirstChild("Dice_"..name)
  if card then
   local face=card.Die face.BackgroundTransparency=1
   for _,s in face:GetChildren() do if s:IsA("UIStroke") then s.Transparency=1 elseif s:IsA("UIGradient") then s.Enabled=false elseif s:IsA("Frame") then s.Visible=false end end
   icon(face,idx,asset)
  end
 end
 for _,d in root.Windows.PotionShopWindow.Body:GetChildren() do
  if POTIONS[string.sub(d.Name,8)] and d:FindFirstChild("Bg") then
   d.Bg.BackgroundTransparency=1 for _,s in d.Bg:GetChildren() do if s:IsA("UIStroke") then s.Transparency=1 end end
  end
 end
 return true
end
return Atlas

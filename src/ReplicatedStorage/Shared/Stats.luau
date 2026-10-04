-- Shared game maths: used by the server for real values and by the client for display.
local GameData = require(script.Parent.GameData)

local Stats = {}

Stats.Pieces = {} -- id -> piece
Stats.PieceList = GameData.Pieces -- ordered common -> rare
Stats.Cars = {}
Stats.Styles = {}
Stats.Potions = {} -- id -> potion
Stats.PotionsByEffect = {}
Stats.Lucky = {}
Stats.Upgrades = {}
Stats.Tiers = {}
Stats.Config = GameData.Config

for _, p in GameData.Pieces do
	Stats.Pieces[p.id] = p
end
for _, c in GameData.Cars do
	Stats.Cars[c.id] = c
end
for _, s in GameData.Styles do
	Stats.Styles[s.id] = s
end
for _, p in GameData.Potions do
	Stats.Potions[p.id] = p
	Stats.PotionsByEffect[p.effect] = p
end
for _, b in GameData.LuckyBlocks do
	Stats.Lucky[b.id] = b
end
for _, u in GameData.Upgrades do
	Stats.Upgrades[u.id] = u
end
for _, t in GameData.Tiers do
	Stats.Tiers[t.id] = t
end

function Stats.hexColor(hex: string): Color3
	return Color3.fromHex(hex)
end

function Stats.upgradeTotal(data, stat: string): number
	local total = 0
	for id in data.Upgrades do
		local u = Stats.Upgrades[id]
		if u and u.stat == stat then
			total += u.value
		end
	end
	return total
end

function Stats.hasUpgrade(data, stat: string): boolean
	for id in data.Upgrades do
		local u = Stats.Upgrades[id]
		if u and u.stat == stat then
			return true
		end
	end
	return false
end

function Stats.potionMult(data, effect: string): number
	local left = data.Potions[effect]
	if left and left > 0 then
		return Stats.PotionsByEffect[effect].mult
	end
	return 1
end

function Stats.rebirthMult(rebirths: number): number
	return 1 + rebirths * GameData.Config.RebirthMoneyBonus
end

function Stats.rebirthCost(rebirths: number): number
	return GameData.Config.RebirthBaseCost * GameData.Config.RebirthCostGrowth ^ rebirths
end

function Stats.friendBoost(friends: number): number
	return math.min(friends * GameData.Config.FriendBoostPer, GameData.Config.FriendBoostMax)
end

function Stats.carMult(data): number
	local car = Stats.Cars[data.EquippedCar] or Stats.Cars.Buggy
	return car.mult
end

-- every money multiplier combined (shown as "xN Multiplier" in the HUD)
function Stats.moneyMult(data, friends: number?): number
	local style = Stats.Styles[data.EquippedStyle]
	local additive = 1 + Stats.upgradeTotal(data, "Money") + (style and style.bonus or 0)
		+ Stats.friendBoost(friends or 0)
	local m = additive * Stats.rebirthMult(data.Rebirths) * Stats.carMult(data)
	m *= Stats.potionMult(data, "Money")
	if data.Passes.X2Money then
		m *= 2
	end
	return m
end

function Stats.luck(data): number
	local l = 1 + Stats.upgradeTotal(data, "Luck")
	l *= Stats.potionMult(data, "Luck")
	if data.Passes.X2Luck then
		l *= 2
	end
	return l
end

function Stats.carSpeed(data): number
	local car = Stats.Cars[data.EquippedCar] or Stats.Cars.Buggy
	return car.speed * (1 + Stats.upgradeTotal(data, "Speed")) * Stats.potionMult(data, "Speed")
end

function Stats.spinCooldown(data): number
	local cd = GameData.Config.BaseSpinCooldown
	for id in data.Upgrades do
		local u = Stats.Upgrades[id]
		if u and u.stat == "SpinSpeed" then
			cd *= (1 - u.value)
		end
	end
	return cd / Stats.potionMult(data, "Spin")
end

function Stats.slots(data): number
	return GameData.Config.BaseSlots + Stats.upgradeTotal(data, "Slots")
end

function Stats.xpForLevel(level: number): number
	return 100 + (level - 1) * 20
end

-- The track uses your best pieces (by rarity), ordered so the rarest parts come last.
function Stats.trackPieces(data): { string }
	local all = {}
	for i = #Stats.PieceList, 1, -1 do
		local p = Stats.PieceList[i]
		local count = data.Parts[p.id] or 0
		for _ = 1, count do
			table.insert(all, p.id)
			if #all >= Stats.slots(data) then
				break
			end
		end
		if #all >= Stats.slots(data) then
			break
		end
	end
	local ordered = {}
	for i = #all, 1, -1 do
		table.insert(ordered, all[i])
	end
	return ordered
end

-- returns true if a newly rolled piece would make it into the track
function Stats.wouldPlace(data, pieceId: string): boolean
	local track = Stats.trackPieces(data)
	if #track < Stats.slots(data) then
		return true
	end
	local worst = Stats.Pieces[track[1]]
	return Stats.Pieces[pieceId].odds > worst.odds
end

return Stats

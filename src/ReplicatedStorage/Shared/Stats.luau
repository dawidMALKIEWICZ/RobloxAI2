-- Shared game maths and grid rules: used by the server for real values and by the client for
-- display / build previews.
local GameData = require(script.Parent.GameData)

local Stats = {}

Stats.Pieces = {} -- id -> piece
Stats.PieceList = GameData.Pieces -- ordered common -> rare
Stats.Cars = {}
Stats.Styles = {}
Stats.Potions = {}
Stats.PotionsByEffect = {}
Stats.Dice = {}
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
for _, d in GameData.Dice do
	Stats.Dice[d.id] = d
end
for _, u in GameData.Upgrades do
	Stats.Upgrades[u.id] = u
end
for _, t in GameData.Tiers do
	Stats.Tiers[t.id] = t
end

-- ------------------------------------------------------------------ multipliers
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

-- product of every running potion's boost for this stat ("Money", "Luck", "Speed", "Spin")
function Stats.potionMult(data, stat: string): number
	local m = 1
	for effect, left in data.Potions do
		local pot = Stats.PotionsByEffect[effect]
		if pot and left > 0 and pot.boosts and pot.boosts[stat] then
			m *= pot.boosts[stat]
		end
	end
	return m
end

function Stats.friendBoost(friends: number): number
	return math.min(friends * GameData.Config.FriendBoostPer, GameData.Config.FriendBoostMax)
end

function Stats.carMult(data): number
	local car = Stats.Cars[data.EquippedCar] or Stats.Cars.Buggy
	return car.mult
end

function Stats.moneyMult(data, friends: number?): number
	local style = Stats.Styles[data.EquippedStyle]
	local additive = 1 + Stats.upgradeTotal(data, "Money") + (style and style.bonus or 0)
		+ Stats.friendBoost(friends or 0)
	local m = additive * Stats.carMult(data) * Stats.potionMult(data, "Money")
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

-- car speed in studs per second (the mini track is small, so cars are slower than real ones)
function Stats.carSpeed(data): number
	local car = Stats.Cars[data.EquippedCar] or Stats.Cars.Buggy
	return car.speed * 0.4 * (1 + Stats.upgradeTotal(data, "Speed")) * Stats.potionMult(data, "Speed")
end

function Stats.rollTime(data): number
	local t = GameData.Config.BaseRollTime
	for id in data.Upgrades do
		local u = Stats.Upgrades[id]
		if u and u.stat == "RollSpeed" then
			t *= (1 - u.value)
		end
	end
	return t / Stats.potionMult(data, "Spin")
end

function Stats.maxElements(data): number
	return GameData.Config.BaseElements + Stats.upgradeTotal(data, "Elements")
end

function Stats.gridSize(data): number
	local size = GameData.Config.BaseGrid
	for id in data.Upgrades do
		local u = Stats.Upgrades[id]
		if u and u.stat == "PlotSize" and u.value > size then
			size = u.value
		end
	end
	return size
end

function Stats.xpForLevel(level: number): number
	return 100 + (level - 1) * 20
end

-- ------------------------------------------------------------------ grid
-- Grid cells are (x, z) in 0..MaxGrid-1. The start tile sits in the centre cell.
-- Sides: 0 = N (-z), 1 = E (+x), 2 = S (+z), 3 = W (-x). Rotation r turns clockwise.
Stats.SIDE_DIR = {
	[0] = { 0, -1 },
	[1] = { 1, 0 },
	[2] = { 0, 1 },
	[3] = { -1, 0 },
}
local PORT_SIDES = { SN = { 2, 0 }, SE = { 2, 1 } }

function Stats.center(): number
	return (GameData.Config.MaxGrid - 1) // 2
end

function Stats.unlockedRange(data): (number, number)
	local n = Stats.gridSize(data)
	local lo = (GameData.Config.MaxGrid - n) // 2
	return lo, lo + n - 1
end

function Stats.inUnlocked(data, x: number, z: number): boolean
	local lo, hi = Stats.unlockedRange(data)
	return x >= lo and x <= hi and z >= lo and z <= hi
end

function Stats.isStart(x: number, z: number): boolean
	local c = Stats.center()
	return x == c and z == c
end

-- the two sides a tile connects (A, B) after rotation
function Stats.ports(pieceId: string, r: number): (number, number)
	local piece = Stats.Pieces[pieceId]
	local ports = PORT_SIDES[piece and piece.ports or "SN"]
	return (ports[1] + r) % 4, (ports[2] + r) % 4
end

function Stats.cellKey(x: number, z: number): string
	return x .. "," .. z
end

function Stats.placedMap(data)
	local map = {}
	for i, t in data.Placed do
		map[Stats.cellKey(t.x, t.z)] = t
	end
	return map
end

-- Follows the road from the start tile. Returns a list of { x, z, id, r, forward } steps and
-- whether the track closes back into the start line.
function Stats.tracePath(data)
	local map = Stats.placedMap(data)
	local c = Stats.center()
	local steps = { { x = c, z = c, id = "Start", r = 0, forward = true } }
	local visited = { [Stats.cellKey(c, c)] = true }
	local x, z, out = c, c, 0 -- start tile drives S -> N
	local closed = false
	for _ = 1, 400 do
		local d = Stats.SIDE_DIR[out]
		local nx, nz = x + d[1], z + d[2]
		local inSide = (out + 2) % 4
		if Stats.isStart(nx, nz) then
			closed = inSide == 2 -- re-entering the start line from behind
			break
		end
		local key = Stats.cellKey(nx, nz)
		local t = map[key]
		if not t or visited[key] then
			break
		end
		local a, b = Stats.ports(t.id, t.r)
		local forward
		if inSide == a then
			forward = true
			out = b
		elseif inSide == b then
			forward = false
			out = a
		else
			break
		end
		visited[key] = true
		table.insert(steps, { x = nx, z = nz, id = t.id, r = t.r, forward = forward })
		x, z = nx, nz
	end
	return steps, closed
end

return Stats

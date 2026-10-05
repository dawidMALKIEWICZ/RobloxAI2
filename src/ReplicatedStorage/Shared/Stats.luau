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
Stats.Mutations = {}
Stats.MutationList = GameData.Mutations or {}
for _, m in Stats.MutationList do
	Stats.Mutations[m.id] = m
end
Stats.FLOOR_H = GameData.Config.FloorHeight or 9

-- ------------------------------------------------------------------ mutations
-- Inventory keys are "PieceId" for plain pieces and "PieceId@Mutation" for mutated ones.
function Stats.splitKey(key: string): (string, string?)
	local id, mut = string.match(key, "^([^@]+)@(.+)$")
	if id then
		return id, mut
	end
	return key, nil
end

function Stats.invKey(id: string, mut: string?): string
	return if mut then id .. "@" .. mut else id
end

function Stats.mutMult(mut: string?): number
	local m = mut and Stats.Mutations[mut]
	return if m then m.mult else 1
end

-- picks a mutation for a fresh roll (nil = plain); rand() returns 0..1
function Stats.rollMutation(luck: number, rand: () -> number): string?
	local k = math.max(1, luck) ^ (GameData.Config.MutationLuckPower or 0.35)
	local list = Stats.MutationList
	for i = #list, 1, -1 do
		if rand() < k / list[i].chance then
			return list[i].id
		end
	end
	return nil
end

-- total count of a piece in the inventory over every mutation
function Stats.ownedCount(data, id: string): number
	local n = 0
	for key, count in data.Inventory do
		if Stats.splitKey(key) == id then
			n += count
		end
	end
	return n
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

-- base = true leaves out potions and the friend boost (used for offline earnings)
function Stats.moneyMult(data, friends: number?, base: boolean?): number
	local style = Stats.Styles[data.EquippedStyle]
	local additive = 1 + Stats.upgradeTotal(data, "Money") + (style and style.bonus or 0)
		+ (if base then 0 else Stats.friendBoost(friends or 0))
	local m = additive * Stats.carMult(data) * (if base then 1 else Stats.potionMult(data, "Money"))
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
function Stats.carSpeed(data, base: boolean?): number
	local car = Stats.Cars[data.EquippedCar] or Stats.Cars.Buggy
	return car.speed * 0.4 * (1 + Stats.upgradeTotal(data, "Speed"))
		* (if base then 1 else Stats.potionMult(data, "Speed"))
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

function Stats.cellKey(x: number, z: number, f: number?): string
	return x .. "," .. z .. "," .. (f or 0)
end

function Stats.floors(data): number
	return data.Floors or 1
end

function Stats.placedMap(data)
	local map = {}
	for _, t in data.Placed do
		map[Stats.cellKey(t.x, t.z, t.f)] = t
	end
	return map
end

-- whether piece `id` may go on cell (x, z) of floor f (0 = ground, 1 = second floor);
-- the inventory is checked separately. Returns false + a message for the player.
function Stats.canPlace(data, x: number, z: number, f: number, id: string, map: any?): (boolean, string?)
	local piece = Stats.Pieces[id]
	if not piece or (f ~= 0 and f ~= 1) then
		return false, "Invalid piece"
	end
	if f == 1 and Stats.floors(data) < 2 then
		return false, "Unlock the 2nd floor first!"
	end
	if not Stats.inUnlocked(data, x, z) then
		return false, "Expand your plot in Skills to build there!"
	end
	local cells = map or Stats.placedMap(data)
	if (f == 0 and Stats.isStart(x, z)) or cells[Stats.cellKey(x, z, f)] then
		return false, "That spot is taken!"
	end
	local tall = Stats.FLOOR_H - 0.3
	if piece.lift then
		if Stats.floors(data) < 2 then
			return false, "Unlock the 2nd floor in Build to use Sky Ramps!"
		end
		if f ~= 0 then
			return false, "Sky Ramps start on the 1st floor!"
		end
	end
	if f == 0 and cells[Stats.cellKey(x, z, 1)] and (piece.height or 0) > tall then
		return false, "Too tall to fit under the 2nd floor!"
	end
	if f == 1 then
		local below = cells[Stats.cellKey(x, z, 0)]
		local bp = below and Stats.Pieces[below.id]
		if bp and (bp.height or 0) > tall then
			return false, "Something tall is in the way below!"
		end
	end
	if #data.Placed >= Stats.maxElements(data) then
		return false, "Element limit reached! Upgrade it in Skills."
	end
	return true
end

-- Follows the road from the start tile. Returns a list of { x, z, f, id, r, m, forward } steps
-- and whether the track closes back into the start line. Sky Ramps (lift pieces) lead from
-- their A port on floor f to their B port on floor f + 1.
function Stats.tracePath(data)
	local map = Stats.placedMap(data)
	local c = Stats.center()
	local steps = { { x = c, z = c, f = 0, id = "Start", r = 0, forward = true } }
	local visited = { [Stats.cellKey(c, c, 0)] = true }
	local x, z, f, out = c, c, 0, 0 -- start tile drives S -> N
	local closed = false
	for _ = 1, 600 do
		local d = Stats.SIDE_DIR[out]
		local nx, nz = x + d[1], z + d[2]
		local inSide = (out + 2) % 4
		if f == 0 and Stats.isStart(nx, nz) then
			closed = inSide == 2 -- re-entering the start line from behind
			break
		end
		local key = Stats.cellKey(nx, nz, f)
		local t = map[key]
		local tileF = f
		local forward, nextOut, nextF
		if t then
			local piece = Stats.Pieces[t.id]
			local lift = piece ~= nil and piece.lift == true
			local a, b = Stats.ports(t.id, t.r)
			if inSide == a then
				forward, nextOut, nextF = true, b, if lift then f + 1 else f
			elseif inSide == b and not lift then
				forward, nextOut, nextF = false, a, f
			else
				break
			end
		elseif f > 0 then
			-- driving down: a Sky Ramp on the floor below whose top end faces us
			key = Stats.cellKey(nx, nz, f - 1)
			t = map[key]
			local piece = t and Stats.Pieces[t.id]
			if not piece or not piece.lift then
				break
			end
			local a, b = Stats.ports(t.id, t.r)
			if inSide ~= b then
				break
			end
			forward, nextOut, nextF, tileF = false, a, f - 1, f - 1
		else
			break
		end
		if visited[key] then
			break
		end
		visited[key] = true
		table.insert(steps, { x = nx, z = nz, f = tileF, id = t.id, r = t.r, m = t.m, forward = forward })
		x, z, f, out = nx, nz, nextF, nextOut
	end
	return steps, closed
end

return Stats

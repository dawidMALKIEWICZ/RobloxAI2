-- All gameplay rules: rolling, building, economy, shops, skills, rewards and Robux products.
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local GameData = require(ReplicatedStorage.Shared.GameData)
local Stats = require(ReplicatedStorage.Shared.Stats)
local Format = require(ReplicatedStorage.Shared.Format)
local DataService = require(script.Parent.DataService)
local PlotService = require(script.Parent.PlotService)
local TrackService = require(script.Parent.TrackService)

local Remotes = ReplicatedStorage:WaitForChild("Remotes")

local GameService = {}

local rng = Random.new()
local MAX_POTION_TIME = 3 * 3600 -- one potion type can be stacked up to 3 hours
local lastRoll: { [Player]: number } = {}
local friends: { [Player]: number } = {}
local productKeyById: { [number]: string } = {}
local passKeyById: { [number]: string } = {}

for k, v in GameData.Products.DevProducts do
	if v.id ~= 0 then
		productKeyById[v.id] = k
	end
end
for k, v in GameData.Products.Gamepasses do
	if v.id ~= 0 then
		passKeyById[v.id] = k
	end
end

-- ------------------------------------------------------------------ helpers
local function notify(player: Player, text: string, color: string?)
	Remotes.Notify:FireClient(player, text, color or "#ffffff")
end

-- money per second; base = without potions and friends (what offline earnings use)
local function income(player: Player, data, base: boolean?): number
	if base then
		return TrackService.income(player, true) * Stats.moneyMult(data, nil, true)
	end
	return TrackService.income(player) * Stats.moneyMult(data, friends[player])
end

local function snapshot(player: Player)
	local data = DataService.get(player)
	if not data then
		return nil
	end
	local f = friends[player] or 0
	local _, closed = Stats.tracePath(data)
	return {
		Data = data,
		MoneyMult = Stats.moneyMult(data, f),
		Luck = Stats.luck(data),
		RollTime = Stats.rollTime(data),
		MaxElements = Stats.maxElements(data),
		GridSize = Stats.gridSize(data),
		Friends = f,
		Income = income(player, data),
		BaseIncome = income(player, data, true),
		Closed = closed,
		ServerTime = os.time(),
	}
end

local function sendUpdate(player: Player)
	local snap = snapshot(player)
	if snap then
		Remotes.DataUpdate:FireClient(player, snap)
	end
end
GameService.sendUpdate = sendUpdate

local function setCash(player: Player, data)
	player:SetAttribute("Cash", data.Cash)
	local ls = player:FindFirstChild("leaderstats")
	if ls then
		(ls:FindFirstChild("Cash") :: StringValue).Value = Format.money(data.Cash)
	end
end

local function addCash(player: Player, data, amount: number)
	data.Cash += amount
	if amount > 0 then
		data.TotalEarned += amount
	end
	setCash(player, data)
end

local function addXP(player: Player, data, xp: number)
	data.XP += xp
	local leveled = false
	while data.XP >= Stats.xpForLevel(data.Level) do
		data.XP -= Stats.xpForLevel(data.Level)
		data.Level += 1
		leveled = true
	end
	if leveled then
		notify(player, "Season Pass level " .. data.Level .. "!", "#ffe14d")
	end
end

-- ------------------------------------------------------------------ rolling
local function roll(luck: number)
	local list = Stats.PieceList
	for i = #list, 2, -1 do
		local p = list[i]
		if rng:NextNumber() < luck / p.odds then
			return p
		end
	end
	return list[1]
end

local function crateRoll()
	local total = 0
	for _, d in GameData.Crate.drops do
		total += d.chance
	end
	local r = rng:NextNumber() * total
	for _, d in GameData.Crate.drops do
		r -= d.chance
		if r <= 0 then
			return Stats.Pieces[d.piece]
		end
	end
	return Stats.Pieces[GameData.Crate.drops[1].piece]
end

-- server-wide shout-outs are throttled so late-game auto rolls cannot flood every client
local lastShout: { [Player]: number } = {}
local function shout(player: Player, pieceId: string, mut: string?, score: number)
	local now = os.clock()
	local gap = if score >= 1e6 then 1.5 else 6
	if lastShout[player] and now - lastShout[player] < gap then
		return
	end
	lastShout[player] = now
	Remotes.RareRoll:FireAllClients(player.DisplayName, pieceId, mut)
end

-- adds a rolled piece to the inventory (it is placed later in build mode); every roll can
-- come out mutated (Golden, Frozen, ... see GameData.Mutations)
local function giveRoll(player: Player, data, piece, source: string, luck: number?)
	local isNew = not data.Discovered[piece.id]
	local mut = Stats.rollMutation(luck or 1, function()
		return rng:NextNumber()
	end)
	local key = Stats.invKey(piece.id, mut)
	data.Inventory[key] = (data.Inventory[key] or 0) + 1
	data.Discovered[piece.id] = true
	if mut then
		data.MutDiscovered = data.MutDiscovered or {}
		data.MutDiscovered[key] = true
	end
	data.Rolls += 1
	addXP(player, data, GameData.Config.XPPerRoll)
	local score = piece.odds * (if mut then Stats.Mutations[mut].chance else 1)
	if piece.odds >= 1000 or score >= 50000 then
		shout(player, piece.id, mut, score)
	end
	return { piece = piece.id, mutation = mut, new = isNew, source = source }
end

-- ------------------------------------------------------------------ rewards
local function grantReward(player: Player, data, rw)
	local t = rw.type
	if t == "Cash" then
		addCash(player, data, rw.amount)
		notify(player, "+" .. Format.money(rw.amount), "#7dff4f")
	elseif t == "Potion" then
		local pot = Stats.Potions[rw.id]
		local count = rw.count or 1
		local dur = rw.duration or pot.duration
		data.Potions[pot.effect] = math.min((data.Potions[pot.effect] or 0) + dur * count, MAX_POTION_TIME)
		TrackService.refreshPath(player, data)
		notify(player, pot.name .. " activated!", if pot.color == "rainbow" then "#ffffff" else pot.color)
	elseif t == "Dice" then
		data.Dice[rw.id] = (data.Dice[rw.id] or 0) + 1
		notify(player, "Got a " .. Stats.Dice[rw.id].name .. "!", "#ffe14d")
	elseif t == "Crate" then
		local result = giveRoll(player, data, crateRoll(), "Crate")
		Remotes.Rolled:FireClient(player, result)
	elseif t == "Car" then
		data.Cars[rw.id] = true
		notify(player, "Unlocked " .. Stats.Cars[rw.id].name .. "!", "#3bb8ff")
	end
end

local function grantProduct(player: Player, key: string): boolean
	local data = DataService.get(player)
	if not data then
		return false
	end
	if key == "X2Money" or key == "X2Luck" or key == "PremiumPass" then
		data.Passes[key] = true
		notify(player, GameData.Products.Gamepasses[key].name .. " unlocked!", "#b54dff")
	elseif key == "StarterPack" then
		if not data.StarterPack then
			data.StarterPack = true
			for _, rw in GameData.StarterPack do
				grantReward(player, data, rw)
			end
		end
	elseif key == "Crate1" then
		grantReward(player, data, { type = "Crate" })
	elseif key == "Crate3" then
		for _ = 1, 3 do
			grantReward(player, data, { type = "Crate" })
		end
	elseif key == "PassSkip" then
		data.Level += 1
		notify(player, "Season Pass level " .. data.Level .. "!", "#ffe14d")
	else
		return false
	end
	sendUpdate(player)
	return true
end

-- ------------------------------------------------------------------ daily
local function dailyState(data)
	local now = os.time()
	local cfg = GameData.Config
	local streak = data.Daily.Streak
	if data.Daily.Last > 0 and now - data.Daily.Last > cfg.DailyResetHours * 3600 then
		streak = 0
	end
	if streak >= 7 then
		streak = 0
	end
	local ready = data.Daily.Last == 0 or now - data.Daily.Last >= cfg.DailyCooldownHours * 3600
	return streak, ready
end

-- ------------------------------------------------------------------ actions
local Actions = {}

function Actions.GetData(player)
	return true, nil, snapshot(player)
end

local function doRoll(player: Player, data, luckMult: number, source: string)
	local luck = Stats.luck(data) * luckMult
	local result = giveRoll(player, data, roll(luck), source, luck)
	sendUpdate(player)
	return true, nil, result
end

function Actions.Roll(player, data)
	local now = os.clock()
	if lastRoll[player] and now - lastRoll[player] < Stats.rollTime(data) * 0.85 then
		return false, "Too fast!"
	end
	lastRoll[player] = now
	return doRoll(player, data, 1, "Roll")
end

function Actions.UseDice(player, data, id)
	local d = Stats.Dice[id]
	if not d or (data.Dice[id] or 0) <= 0 then
		return false, "You don't have this dice!"
	end
	data.Dice[id] -= 1
	return doRoll(player, data, d.luck, d.name)
end

function Actions.SetAuto(player, data, on)
	-- Auto Roll is available to every player from the start.
	data.AutoRoll = on == true
	sendUpdate(player)
	return true
end

function Actions.Place(player, data, args)
	if type(args) ~= "table" then
		return false
	end
	local x, z, r, f, key = tonumber(args.x), tonumber(args.z), tonumber(args.r), tonumber(args.f or 0), args.id
	if not x or not z or not r or not f or type(key) ~= "string" or #key > 40 then
		return false, "Invalid piece"
	end
	for _, v in { x, z, r, f } do
		if v ~= v or math.abs(v) == math.huge then
			return false, "Invalid piece"
		end
	end
	local id, mut = Stats.splitKey(key)
	if not Stats.Pieces[id] or (mut and not Stats.Mutations[mut]) then
		return false, "Invalid piece"
	end
	x, z, r, f = math.floor(x), math.floor(z), math.floor(r) % 4, math.floor(f)
	local ok, msg = Stats.canPlace(data, x, z, f, id)
	if not ok then
		return false, msg
	end
	if (data.Inventory[key] or 0) <= 0 then
		return false, "You have no " .. Stats.Pieces[id].name .. " left!"
	end
	data.Inventory[key] -= 1
	if data.Inventory[key] <= 0 and mut then
		data.Inventory[key] = nil
	end
	table.insert(data.Placed, { x = x, z = z, r = r, id = id, f = if f ~= 0 then f else nil, m = mut })
	local plot = PlotService.get(player)
	if plot then
		local born = workspace:GetServerTimeNow()
		if f == 1 then
			PlotService.syncPillars(plot, data.Placed, born)
		end
		TrackService.spawnTile(plot, x, z, r, id, f, mut, born)
	end
	TrackService.refreshPath(player, data)
	sendUpdate(player)
	return true
end

function Actions.Remove(player, data, args)
	if type(args) ~= "table" then
		return false
	end
	local x, z, f = tonumber(args.x), tonumber(args.z), tonumber(args.f or 0) or 0
	if not x or not z then
		return false
	end
	for i, t in data.Placed do
		if t.x == x and t.z == z and (t.f or 0) == f then
			table.remove(data.Placed, i)
			local key = Stats.invKey(t.id, t.m)
			data.Inventory[key] = (data.Inventory[key] or 0) + 1
			local plot = PlotService.get(player)
			if plot then
				TrackService.removeTile(plot, x, z, f)
				if f == 1 then
					PlotService.syncPillars(plot, data.Placed)
				end
			end
			TrackService.refreshPath(player, data)
			sendUpdate(player)
			return true
		end
	end
	return false, "Nothing to remove there"
end

-- the second track floor: towers, girders and free Sky Ramps
function Actions.BuyFloor(player, data)
	if Stats.floors(data) >= 2 then
		return false, "You already own the 2nd floor!"
	end
	local price = GameData.Config.SecondFloorPrice
	if data.Cash < price then
		return false, "You need " .. Format.money(price) .. " for the 2nd floor!"
	end
	addCash(player, data, -price)
	data.Floors = 2
	local lifts = GameData.Config.SecondFloorLifts or 2
	data.Inventory.Lift = (data.Inventory.Lift or 0) + lifts
	data.Discovered.Lift = true
	local plot = PlotService.get(player)
	if plot then
		PlotService.buildFloorFrame(plot, true, workspace:GetServerTimeNow())
	end
	sendUpdate(player)
	return true, "2nd floor unlocked! +" .. lifts .. " Sky Ramps"
end

-- Dice fusion: FuseCount dice of one kind -> one die of the next kind (sometimes two kinds up)
function Actions.FuseDice(player, data, id)
	local need = GameData.Config.FuseCount or 3
	local index = nil
	for i, d in GameData.Dice do
		if d.id == id then
			index = i
		end
	end
	if not index then
		return false, "Unknown dice"
	end
	if index >= #GameData.Dice then
		return false, "This is already the best dice!"
	end
	if (data.Dice[id] or 0) < need then
		return false, "You need " .. need .. " " .. GameData.Dice[index].name .. " to fuse!"
	end
	data.Dice[id] -= need
	local jackpot = index + 2 <= #GameData.Dice and rng:NextNumber() < (GameData.Config.FuseJackpot or 0.1)
	local out = GameData.Dice[index + (if jackpot then 2 else 1)]
	data.Dice[out.id] = (data.Dice[out.id] or 0) + 1
	data.Fusions = (data.Fusions or 0) + 1
	addXP(player, data, GameData.Config.XPPerRoll * 5)
	sendUpdate(player)
	return true, nil, { from = id, to = out.id, jackpot = jackpot }
end

function Actions.BuyCar(player, data, id)
	local car = Stats.Cars[id]
	if not car then
		return false, "Unknown car"
	end
	if not data.Cars[id] then
		if data.Cash < car.price then
			return false, "Not enough cash!"
		end
		addCash(player, data, -car.price)
		data.Cars[id] = true
	end
	data.EquippedCar = id
	TrackService.setCar(player, id)
	TrackService.refreshPath(player, data)
	sendUpdate(player)
	return true, car.name .. " equipped!"
end

function Actions.BuyStyle(player, data, id)
	local style = Stats.Styles[id]
	if not style then
		return false, "Unknown style"
	end
	if not data.Styles[id] then
		if data.Cash < style.price then
			return false, "Not enough cash!"
		end
		addCash(player, data, -style.price)
		data.Styles[id] = true
	end
	data.EquippedStyle = id
	local plot = PlotService.get(player)
	if plot then
		PlotService.applyStyle(plot, id)
	end
	sendUpdate(player)
	return true, style.name .. " applied!"
end

function Actions.BuyPotion(player, data, id)
	local pot = Stats.Potions[id]
	if not pot then
		return false, "Unknown potion"
	end
	if data.Cash < pot.price then
		return false, "Not enough cash!"
	end
	local left = data.Potions[pot.effect] or 0
	if left + pot.duration > MAX_POTION_TIME then
		return false, "That potion is already stacked to the limit!"
	end
	addCash(player, data, -pot.price)
	data.Potions[pot.effect] = left + pot.duration
	TrackService.refreshPath(player, data)
	sendUpdate(player)
	return true, pot.name .. " activated!"
end

function Actions.BuyDice(player, data, id)
	local d = Stats.Dice[id]
	if not d then
		return false, "Unknown dice"
	end
	if data.Cash < d.price then
		return false, "Not enough cash!"
	end
	addCash(player, data, -d.price)
	data.Dice[id] = (data.Dice[id] or 0) + 1
	sendUpdate(player)
	return true, "Bought a " .. d.name .. "!"
end

function Actions.BuyUpgrade(player, data, id)
	local u = Stats.Upgrades[id]
	if not u then
		return false, "Unknown skill"
	end
	if data.Upgrades[id] then
		return false, "Already owned"
	end
	if u.requires and not data.Upgrades[u.requires] then
		return false, "Unlock " .. Stats.Upgrades[u.requires].name .. " first!"
	end
	if data.Cash < u.cost then
		return false, "Not enough cash!"
	end
	addCash(player, data, -u.cost)
	data.Upgrades[id] = true
	if u.stat == "PlotSize" then
		local plot = PlotService.get(player)
		if plot then
			PlotService.buildPad(plot, Stats.gridSize(data))
		end
	end
	TrackService.refreshPath(player, data)
	sendUpdate(player)
	return true, u.name .. " unlocked!"
end

function Actions.ClaimDaily(player, data)
	local streak, ready = dailyState(data)
	if not ready then
		return false, "Come back later!"
	end
	local day = streak + 1
	data.Daily.Streak = day
	data.Daily.Last = os.time()
	grantReward(player, data, GameData.Daily[day])
	sendUpdate(player)
	return true, "Day " .. day .. " claimed!"
end

function Actions.ClaimPass(player, data)
	local count = 0
	for _, entry in GameData.Pass do
		local lvl = entry.level
		local k = tostring(lvl)
		if lvl <= data.Level then
			if not data.PassClaimed.free[k] then
				data.PassClaimed.free[k] = true
				grantReward(player, data, entry.free)
				count += 1
			end
			if data.Passes.PremiumPass and not data.PassClaimed.premium[k] then
				data.PassClaimed.premium[k] = true
				grantReward(player, data, entry.premium)
				count += 1
			end
		end
	end
	sendUpdate(player)
	if count == 0 then
		return false, "Nothing to claim yet!"
	end
	return true, "Claimed " .. count .. " rewards!"
end

-- client settings (music, sound effects, effect quality); only known keys are stored
function Actions.SetSettings(player, data, settings)
	if type(settings) ~= "table" then
		return false
	end
	data.Settings = data.Settings or {}
	if type(settings.Music) == "boolean" then
		data.Settings.Music = settings.Music
	end
	if type(settings.Sfx) == "boolean" then
		data.Settings.Sfx = settings.Sfx
	end
	if settings.Vfx == "High" or settings.Vfx == "Low" then
		data.Settings.Vfx = settings.Vfx
	end
	return true
end

function Actions.Teleport(player, _data, target)
	PlotService.teleport(player, target)
	return true
end

function Actions.Purchase(player, data, key)
	local pass = GameData.Products.Gamepasses[key]
	local prod = GameData.Products.DevProducts[key]
	local entry = pass or prod
	if not entry then
		return false, "Unknown product"
	end
	if pass and data.Passes[key] then
		return false, "You already own this!"
	end
	if key == "StarterPack" and data.StarterPack then
		return false, "You already bought the Starter Pack!"
	end
	if entry.id == 0 then
		if RunService:IsStudio() then
			grantProduct(player, key)
			return true, "(Studio test purchase) " .. entry.name
		end
		return false, "This item is not available yet."
	end
	if pass then
		MarketplaceService:PromptGamePassPurchase(player, entry.id)
	else
		MarketplaceService:PromptProductPurchase(player, entry.id)
	end
	return true
end

-- ------------------------------------------------------------------ lifecycle
local function countFriends(player: Player)
	local n = 0
	for _, other in Players:GetPlayers() do
		if other ~= player and other.Parent then
			local ok, isFriend = pcall(function()
				return player:IsFriendsWithAsync(other.UserId)
			end)
			if ok and isFriend then
				n += 1
			end
		end
	end
	if player.Parent then
		friends[player] = n
	end
end

local function refreshFriends()
	for _, p in Players:GetPlayers() do
		task.spawn(function()
			countFriends(p)
			sendUpdate(p)
		end)
	end
end

function GameService.onEarn(player: Player, pieceId: string, pos: Vector3, mult: number?)
	local data = DataService.get(player)
	local piece = Stats.Pieces[pieceId]
	if not data or not piece then
		return
	end
	local amount = math.max(1, math.floor(piece.value * (mult or 1) * Stats.moneyMult(data, friends[player])))
	addCash(player, data, amount)
	Remotes.Earned:FireClient(player, amount, pos)
end

function GameService.playerAdded(player: Player)
	local data = DataService.load(player)
	if not player.Parent or DataService.get(player) ~= data then
		return
	end
	-- read before anything can touch them (the income loop rewrites LastIncome every second)
	local lastOnline, lastIncome = data.LastOnline, data.LastIncome
	local ls = Instance.new("Folder")
	ls.Name = "leaderstats"
	local cash = Instance.new("StringValue")
	cash.Name = "Cash"
	cash.Parent = ls
	ls.Parent = player
	setCash(player, data)

	for key, v in GameData.Products.Gamepasses do
		if v.id ~= 0 then
			local ok, owns = pcall(function()
				return MarketplaceService:UserOwnsGamePassAsync(player.UserId, v.id)
			end)
			if ok and owns then
				data.Passes[key] = true
			end
		end
	end

	local plot = PlotService.claim(player)
	if plot then
		PlotService.applyStyle(plot, data.EquippedStyle)
		PlotService.buildPad(plot, Stats.gridSize(data))
		TrackService.load(player, data)
	else
		notify(player, "Server is full - no free plot!", "#ff3b6b")
	end

	-- offline earnings (base income: potions and friends do not count while away)
	if lastOnline > 0 and lastIncome > 0 then
		local cfg = GameData.Config
		local away = math.max(0, os.time() - lastOnline)
		local secs = math.min(away, cfg.OfflineMaxHours * 3600)
		local earned = math.floor(lastIncome * secs * cfg.OfflineRate)
		if earned > 0 and away >= 60 then
			addCash(player, data, earned)
			task.delay(2.5, function()
				if player.Parent then
					Remotes.Offline:FireClient(player, { amount = earned, away = away, paid = secs,
						cap = cfg.OfflineMaxHours * 3600, rate = cfg.OfflineRate })
				end
			end)
		end
	end

	local function onChar(char: Model)
		char:WaitForChild("HumanoidRootPart")
		task.wait(0.1)
		PlotService.teleport(player)
	end
	player.CharacterAdded:Connect(onChar)
	if player.Character then
		task.spawn(onChar, player.Character)
	end
	refreshFriends()
	sendUpdate(player)
end

function GameService.playerRemoving(player: Player)
	local data = DataService.get(player)
	if data then
		data.LastIncome = income(player, data, true)
		data.LastOnline = os.time()
	end
	TrackService.clear(player)
	PlotService.release(player)
	DataService.release(player)
	lastRoll[player] = nil
	lastShout[player] = nil
	friends[player] = nil
	-- wait until the player is really gone so they no longer count as anyone's friend
	task.defer(refreshFriends)
end

-- ------------------------------------------------------------------ test commands
-- Only in Studio or for the game's creator: /alltracks /cash [amount] /dice /potions
local OWNER_IDS = { [2811698523] = true }
local function canTest(player: Player): boolean
	return RunService:IsStudio() or player.UserId == game.CreatorId or OWNER_IDS[player.UserId] == true
end

local lastCommand: { [Player]: { [string]: number } } = {}
local function runCommand(player: Player, text: string)
	if not canTest(player) then
		return
	end
	local data = DataService.get(player)
	if not data then
		return
	end
	local cmd, arg = string.match(string.lower(text), "^/(%a+)%s*(%S*)")
	if not cmd then
		return
	end
	-- the same command can arrive through both chat systems; run it once
	local seen = lastCommand[player] or {}
	lastCommand[player] = seen
	if seen[cmd] and os.clock() - seen[cmd] < 1 then
		return
	end
	seen[cmd] = os.clock()
	if cmd == "alltracks" then
		local n = tonumber(arg) or 25
		for _, pc in GameData.Pieces do
			data.Inventory[pc.id] = (data.Inventory[pc.id] or 0) + n
			data.Discovered[pc.id] = true
		end
		notify(player, "Test: +" .. n .. " of every track piece!", "#7dff6b")
	elseif cmd == "cash" then
		addCash(player, data, tonumber(arg) or 1e9)
		notify(player, "Test: cash added!", "#7dff6b")
	elseif cmd == "dice" then
		for _, d in GameData.Dice do
			data.Dice[d.id] = (data.Dice[d.id] or 0) + (tonumber(arg) or 5)
		end
		notify(player, "Test: dice added!", "#7dff6b")
	elseif cmd == "potions" then
		for _, pot in GameData.Potions do
			data.Potions[pot.effect] = math.max(data.Potions[pot.effect] or 0, pot.duration)
		end
		TrackService.refreshPath(player, data)
		notify(player, "Test: every potion is active!", "#7dff6b")
	elseif cmd == "mutations" then
		local n = tonumber(arg) or 2
		for _, pc in GameData.Pieces do
			for _, m in Stats.MutationList do
				local key = Stats.invKey(pc.id, m.id)
				data.Inventory[key] = (data.Inventory[key] or 0) + n
			end
			data.Discovered[pc.id] = true
		end
		notify(player, "Test: +" .. n .. " of every piece in every mutation!", "#7dff6b")
	elseif cmd == "floor" then
		if Stats.floors(data) < 2 then
			data.Cash += GameData.Config.SecondFloorPrice
			Actions.BuyFloor(player, data)
		end
		notify(player, "Test: 2nd floor unlocked!", "#7dff6b")
	elseif cmd == "offline" then
		local hours = math.clamp(tonumber(arg) or 2, 0.02, 24)
		local cfg = GameData.Config
		local base = math.max(income(player, data, true), 1)
		local away = math.floor(hours * 3600)
		local secs = math.min(away, cfg.OfflineMaxHours * 3600)
		local earned = math.floor(base * secs * cfg.OfflineRate)
		addCash(player, data, earned)
		Remotes.Offline:FireClient(player, { amount = earned, away = away, paid = secs,
			cap = cfg.OfflineMaxHours * 3600, rate = cfg.OfflineRate })
	else
		return
	end
	sendUpdate(player)
end

function Actions.DevCommand(player, _data, text)
	if type(text) ~= "string" or #text > 40 then
		return false
	end
	if not canTest(player) then
		return false, "Test commands only work in Studio or for the game owner."
	end
	runCommand(player, text)
	return true
end

local function setupCommands()
	-- chat commands are created by the client (Actions.DevCommand); Chatted is a fallback for
	-- legacy chat. runCommand ignores a second copy of the same command within a second.
	local function hook(player: Player)
		player.Chatted:Connect(function(msg)
			runCommand(player, msg)
		end)
	end
	for _, p in Players:GetPlayers() do
		hook(p)
	end
	Players.PlayerAdded:Connect(hook)
	Players.PlayerRemoving:Connect(function(p)
		lastCommand[p] = nil
	end)
end

function GameService.start()
	setupCommands()
	-- token bucket per player: bursts of 20 requests, refilled at 12 per second
	local buckets: { [Player]: { tokens: number, t: number } } = {}
	Players.PlayerRemoving:Connect(function(p)
		buckets[p] = nil
	end)
	Remotes.Request.OnServerInvoke = function(player, action, arg)
		local now = os.clock()
		local bucket = buckets[player] or { tokens = 20, t = now }
		buckets[player] = bucket
		bucket.tokens = math.min(20, bucket.tokens + (now - bucket.t) * 12)
		bucket.t = now
		if bucket.tokens < 1 then
			return false, "Slow down!"
		end
		bucket.tokens -= 1
		if type(action) ~= "string" then
			return false
		end
		local fn = Actions[action]
		local data = DataService.get(player)
		if not fn or not data then
			return false, "Not ready"
		end
		local ok, a, b, c = pcall(fn, player, data, arg)
		if not ok then
			warn("[GameService]", action, a)
			return false, "Something went wrong"
		end
		return a, b, c
	end

	TrackService.setEarnHandler(GameService.onEarn)
	TrackService.start(DataService.get)

	-- potion timers + income bookkeeping
	task.spawn(function()
		while true do
			task.wait(1)
			for _, player in Players:GetPlayers() do
				local data = DataService.get(player)
				if data and TrackService.income(player) > 0 then
					data.LastIncome = income(player, data, true)
				end
				if data then
					local expired = false
					for effect, left in data.Potions do
						if left > 0 then
							data.Potions[effect] = left - 1
							if left - 1 <= 0 then
								expired = true
							end
						end
					end
					if expired then
						notify(player, "A potion ran out.", "#cfd8ff")
						TrackService.refreshPath(player, data)
						sendUpdate(player)
					end
				end
			end
		end
	end)

	MarketplaceService.ProcessReceipt = function(info)
		local player = Players:GetPlayerByUserId(info.PlayerId)
		local key = productKeyById[info.ProductId]
		if not player or not key or not DataService.get(player) then
			return Enum.ProductPurchaseDecision.NotProcessedYet
		end
		if grantProduct(player, key) then
			task.spawn(DataService.save, player)
			return Enum.ProductPurchaseDecision.PurchaseGranted
		end
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
		local key = passKeyById[passId]
		if purchased and key then
			grantProduct(player, key)
		end
	end)
end

return GameService

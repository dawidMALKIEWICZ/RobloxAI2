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

local function income(player: Player, data): number
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

-- adds a rolled piece to the inventory (it is placed later in build mode)
local function giveRoll(player: Player, data, piece, source: string)
	local isNew = not data.Discovered[piece.id]
	data.Inventory[piece.id] = (data.Inventory[piece.id] or 0) + 1
	data.Discovered[piece.id] = true
	data.Rolls += 1
	addXP(player, data, GameData.Config.XPPerRoll)
	if piece.odds >= 1000 then
		Remotes.RareRoll:FireAllClients(player.DisplayName, piece.id)
	end
	return { piece = piece.id, new = isNew, source = source }
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
		data.Potions[pot.effect] = (data.Potions[pot.effect] or 0) + dur * count
		notify(player, pot.name .. " activated!", pot.color)
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
	local result = giveRoll(player, data, roll(Stats.luck(data) * luckMult), source)
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
	local x, z, r, id = tonumber(args.x), tonumber(args.z), tonumber(args.r), args.id
	if not x or not z or not r or type(id) ~= "string" or not Stats.Pieces[id] then
		return false, "Invalid piece"
	end
	x, z, r = math.floor(x), math.floor(z), math.floor(r) % 4
	if not Stats.inUnlocked(data, x, z) then
		return false, "Expand your plot in Skills to build there!"
	end
	if Stats.isStart(x, z) or Stats.placedMap(data)[Stats.cellKey(x, z)] then
		return false, "That spot is taken!"
	end
	if (data.Inventory[id] or 0) <= 0 then
		return false, "You have no " .. Stats.Pieces[id].name .. " left!"
	end
	if #data.Placed >= Stats.maxElements(data) then
		return false, "Element limit reached! Upgrade it in Skills."
	end
	data.Inventory[id] -= 1
	table.insert(data.Placed, { x = x, z = z, r = r, id = id })
	local plot = PlotService.get(player)
	if plot then
		TrackService.spawnTile(plot, x, z, r, id)
	end
	TrackService.refreshPath(player, data)
	sendUpdate(player)
	return true
end

function Actions.Remove(player, data, args)
	if type(args) ~= "table" then
		return false
	end
	local x, z = tonumber(args.x), tonumber(args.z)
	if not x or not z then
		return false
	end
	for i, t in data.Placed do
		if t.x == x and t.z == z then
			table.remove(data.Placed, i)
			data.Inventory[t.id] = (data.Inventory[t.id] or 0) + 1
			local plot = PlotService.get(player)
			if plot then
				TrackService.removeTile(plot, x, z)
			end
			TrackService.refreshPath(player, data)
			sendUpdate(player)
			return true
		end
	end
	return false, "Nothing to remove there"
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
		if other ~= player then
			local ok, isFriend = pcall(function()
				return player:IsFriendsWithAsync(other.UserId)
			end)
			if ok and isFriend then
				n += 1
			end
		end
	end
	friends[player] = n
end

local function refreshFriends()
	for _, p in Players:GetPlayers() do
		task.spawn(function()
			countFriends(p)
			sendUpdate(p)
		end)
	end
end

function GameService.onEarn(player: Player, pieceId: string, pos: Vector3)
	local data = DataService.get(player)
	local piece = Stats.Pieces[pieceId]
	if not data or not piece then
		return
	end
	local amount = math.max(1, math.floor(piece.value * Stats.moneyMult(data, friends[player])))
	addCash(player, data, amount)
	Remotes.Earned:FireClient(player, amount, pos)
end

function GameService.playerAdded(player: Player)
	local data = DataService.load(player)
	if not player.Parent then
		return
	end
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

	-- offline earnings
	if data.LastOnline > 0 and data.LastIncome > 0 then
		local cfg = GameData.Config
		local secs = math.min(os.time() - data.LastOnline, cfg.OfflineMaxHours * 3600)
		local earned = math.floor(data.LastIncome * secs * cfg.OfflineRate)
		if earned > 0 then
			addCash(player, data, earned)
			task.delay(3, notify, player, "Welcome back! Offline earnings: +" .. Format.money(earned),
				"#7dff4f")
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
		data.LastIncome = income(player, data)
		data.LastOnline = os.time()
	end
	TrackService.clear(player)
	PlotService.release(player)
	DataService.release(player)
	lastRoll[player] = nil
	friends[player] = nil
	refreshFriends()
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
		notify(player, "Test: every potion is active!", "#7dff6b")
	else
		return
	end
	sendUpdate(player)
end

local function setupCommands()
	local TextChatService = game:GetService("TextChatService")
	for _, name in { "alltracks", "cash", "dice", "potions" } do
		local c = Instance.new("TextChatCommand")
		c.Name = "TrackRNG_" .. name
		c.PrimaryAlias = "/" .. name
		c.Parent = TextChatService
		c.Triggered:Connect(function(source, text)
			local player = Players:GetPlayerByUserId(source.UserId)
			if player then
				runCommand(player, text)
			end
		end)
	end
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
				if data then
					data.LastIncome = income(player, data)
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

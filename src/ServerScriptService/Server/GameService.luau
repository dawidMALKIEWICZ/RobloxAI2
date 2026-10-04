-- All gameplay rules: spinning, economy, shops, upgrades, rewards, rebirths and Robux products.
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
local lastSpin: { [Player]: number } = {}
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

local function snapshot(player: Player)
	local data = DataService.get(player)
	if not data then
		return nil
	end
	local f = friends[player] or 0
	return {
		Data = data,
		MoneyMult = Stats.moneyMult(data, f),
		Luck = Stats.luck(data),
		Speed = Stats.carSpeed(data),
		Cooldown = Stats.spinCooldown(data),
		Slots = Stats.slots(data),
		Track = Stats.trackPieces(data),
		Friends = f,
		RebirthCost = Stats.rebirthCost(data.Rebirths),
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
		(ls:FindFirstChild("Cash") :: StringValue).Value = Format.money(data.Cash);
		(ls:FindFirstChild("Rebirths") :: IntValue).Value = data.Rebirths
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
		notify(player, "Level up! You are now level " .. data.Level, "#ffe14d")
	end
end

local function addLevels(player: Player, data, n: number)
	data.Level += n
	notify(player, "+" .. n .. " Levels!", "#ffe14d")
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

-- Adds a rolled piece to the player and rebuilds their track when it improves it.
local function giveRoll(player: Player, data, piece, source: string)
	local placed = Stats.wouldPlace(data, piece.id)
	local isNew = not data.Discovered[piece.id]
	data.Parts[piece.id] = (data.Parts[piece.id] or 0) + 1
	data.Discovered[piece.id] = true
	data.Spins += 1
	local bonus = 0
	if not placed then
		bonus = math.floor(piece.value * 2 * Stats.moneyMult(data, friends[player]))
		addCash(player, data, bonus)
	end
	addXP(player, data, GameData.Config.XPPerSpin)
	if placed then
		TrackService.refresh(player, data)
	end
	if piece.odds >= 1000 then
		for _, other in Players:GetPlayers() do
			notify(other, player.DisplayName .. " rolled " .. piece.name .. " (1 in "
				.. Format.commas(piece.odds) .. ")!", Stats.Tiers[piece.tier].color)
		end
	end
	local result = {
		piece = piece.id,
		placed = placed,
		bonus = bonus,
		new = isNew,
		source = source,
	}
	return result
end

-- ------------------------------------------------------------------ rewards
local function grantReward(player: Player, data, rw)
	local t = rw.type
	if t == "Cash" then
		local amount = math.floor(rw.amount * Stats.rebirthMult(data.Rebirths))
		addCash(player, data, amount)
		notify(player, "+" .. Format.money(amount), "#7dff4f")
	elseif t == "Potion" then
		local pot = Stats.Potions[rw.id]
		local count = rw.count or 1
		local dur = rw.duration or pot.duration
		data.Potions[pot.effect] = (data.Potions[pot.effect] or 0) + dur * count
		notify(player, pot.name .. " activated!", pot.color)
	elseif t == "Lucky" then
		data.LuckyInv[rw.id] = (data.LuckyInv[rw.id] or 0) + 1
		notify(player, "Got a " .. Stats.Lucky[rw.id].name .. "!", Stats.Lucky[rw.id].color)
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
	elseif key == "Levels5" then
		addLevels(player, data, 5)
	elseif key == "Levels10" then
		addLevels(player, data, 10)
	elseif key == "Levels25" then
		addLevels(player, data, 25)
	elseif key == "PassSkip" then
		addLevels(player, data, 1)
	elseif key == "SkipRebirth" then
		data.Rebirths += 1
		setCash(player, data)
		notify(player, "Rebirth " .. data.Rebirths .. "! Stats kept.", "#b54dff")
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

function Actions.Spin(player, data)
	local now = os.clock()
	local cd = Stats.spinCooldown(data)
	if lastSpin[player] and now - lastSpin[player] < cd * 0.85 then
		return false, "Too fast!"
	end
	lastSpin[player] = now
	local result = giveRoll(player, data, roll(Stats.luck(data)), "Spin")
	sendUpdate(player)
	return true, nil, result
end

function Actions.SetAuto(player, data, on)
	if on and not Stats.hasUpgrade(data, "AutoSpin") then
		return false, "Unlock Auto Spin in Upgrades!"
	end
	data.AutoSpin = on == true
	sendUpdate(player)
	return true
end

function Actions.BuyCar(player, data, id)
	local car = Stats.Cars[id]
	if not car then
		return false, "Unknown car"
	end
	if data.Cars[id] then
		data.EquippedCar = id
		TrackService.setCar(player, id)
		sendUpdate(player)
		return true, car.name .. " equipped!"
	end
	if data.Cash < car.price then
		return false, "Not enough cash!"
	end
	addCash(player, data, -car.price)
	data.Cars[id] = true
	data.EquippedCar = id
	TrackService.setCar(player, id)
	sendUpdate(player)
	return true, "Bought " .. car.name .. "!"
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
	addCash(player, data, -pot.price)
	data.Potions[pot.effect] = (data.Potions[pot.effect] or 0) + pot.duration
	sendUpdate(player)
	return true, pot.name .. " activated!"
end

function Actions.BuyLucky(player, data, id)
	local b = Stats.Lucky[id]
	if not b then
		return false, "Unknown block"
	end
	if data.Cash < b.price then
		return false, "Not enough cash!"
	end
	addCash(player, data, -b.price)
	data.LuckyInv[id] = (data.LuckyInv[id] or 0) + 1
	sendUpdate(player)
	return true, "Bought " .. b.name .. "!"
end

function Actions.OpenLucky(player, data, id)
	local b = Stats.Lucky[id]
	if not b or (data.LuckyInv[id] or 0) <= 0 then
		return false, "You don't have this block!"
	end
	data.LuckyInv[id] -= 1
	local result = giveRoll(player, data, roll(Stats.luck(data) * b.luck), b.name)
	sendUpdate(player)
	return true, nil, result
end

function Actions.BuyUpgrade(player, data, id)
	local u = Stats.Upgrades[id]
	if not u then
		return false, "Unknown upgrade"
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
	if u.stat == "Slots" then
		TrackService.refresh(player, data)
	end
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

function Actions.Rebirth(player, data)
	local cost = Stats.rebirthCost(data.Rebirths)
	if data.Cash < cost then
		return false, "You need " .. Format.money(cost) .. " to rebirth!"
	end
	data.Cash = 0
	data.Parts = {}
	data.Rebirths += 1
	setCash(player, data)
	TrackService.refresh(player, data, true)
	sendUpdate(player)
	return true, "Rebirth " .. data.Rebirths .. "! Money x" .. Stats.rebirthMult(data.Rebirths)
end

function Actions.Teleport(player)
	PlotService.teleport(player)
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
	local amount = math.floor(piece.value * Stats.moneyMult(data, friends[player]))
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
	local reb = Instance.new("IntValue")
	reb.Name = "Rebirths"
	reb.Parent = ls
	ls.Parent = player
	setCash(player, data)

	-- gamepasses bought on the website
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
		TrackService.refresh(player, data, true)
	else
		notify(player, "Server is full - no free plot!", "#ff3b6b")
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
	TrackService.clear(player)
	PlotService.release(player)
	DataService.release(player)
	lastSpin[player] = nil
	friends[player] = nil
	refreshFriends()
end

function GameService.start()
	Remotes.Request.OnServerInvoke = function(player, action, arg)
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

	-- potion timers
	task.spawn(function()
		while true do
			task.wait(1)
			for _, player in Players:GetPlayers() do
				local data = DataService.get(player)
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

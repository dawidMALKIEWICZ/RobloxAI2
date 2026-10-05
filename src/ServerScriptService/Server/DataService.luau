-- Loads / saves player data with DataStoreService. Works in Studio without API access
-- (data is then kept in memory only).
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local DataService = {}

local STORE_NAME = "TrackRNG_v2"
local AUTOSAVE = 60

local store = nil
do
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(STORE_NAME)
	end)
	if ok then
		store = result
	else
		warn("[DataService] DataStore unavailable, data will not persist:", result)
	end
end

local profiles: { [Player]: any } = {}
local loaded: { [Player]: boolean } = {}

local function defaults()
	return {
		Version = 2,
		Cash = 0,
		TotalEarned = 0,
		Level = 1,
		XP = 0,
		Rolls = 0,
		Inventory = { Straight = 8, Turn = 4 }, -- pieceId -> count (not placed)
		Placed = {}, -- list of { x, z, r, id }
		Discovered = { Straight = true, Turn = true },
		Cars = { Buggy = true },
		EquippedCar = "Buggy",
		Styles = { Classic = true },
		EquippedStyle = "Classic",
		Upgrades = {}, -- upgradeId -> true
		Potions = {}, -- effect -> seconds left
		Dice = {}, -- diceId -> count
		Daily = { Streak = 0, Last = 0 },
		PassClaimed = { free = {}, premium = {} },
		Passes = {}, -- X2Money / X2Luck / PremiumPass -> true
		StarterPack = false,
		AutoRoll = false,
		Settings = { Music = true, Sfx = true, Vfx = "High" },
		Floors = 1, -- 2 once the second track floor is bought
		Fusions = 0,
		LastOnline = 0,
		LastIncome = 0, -- money per second, used for offline earnings
	}
end

local function reconcile(data, template)
	for k, v in template do
		if data[k] == nil then
			data[k] = if type(v) == "table" then table.clone(v) else v
		elseif type(v) == "table" and type(data[k]) == "table" and k ~= "Inventory"
			and k ~= "Discovered" then
			reconcile(data[k], v)
		end
	end
	return data
end

local function key(userId: number): string
	return "player_" .. userId
end

function DataService.load(player: Player)
	local data = nil
	local loadOk = store == nil
	if store then
		for attempt = 1, 3 do
			local ok, result = pcall(function()
				return store:GetAsync(key(player.UserId))
			end)
			if ok then
				data = result
				loadOk = true
				break
			end
			warn("[DataService] load failed (attempt " .. attempt .. "):", result)
			task.wait(1)
		end
	end
	data = reconcile(data or {}, defaults())
	if not player.Parent then
		return data -- left while loading: keep nothing around
	end
	profiles[player] = data
	-- a profile that failed to load is never saved, so it cannot overwrite the real save
	loaded[player] = loadOk
	if not loadOk then
		task.defer(function()
			player:Kick("Could not load your save (Roblox data servers are busy). Please rejoin!")
		end)
	end
	return data
end

function DataService.get(player: Player)
	return profiles[player]
end

function DataService.save(player: Player)
	local data = profiles[player]
	if not data or not store or not loaded[player] then
		return
	end
	data.LastOnline = os.time()
	local ok, err = pcall(function()
		store:UpdateAsync(key(player.UserId), function()
			return data
		end)
	end)
	if not ok then
		warn("[DataService] save failed:", err)
	end
end

function DataService.release(player: Player)
	DataService.save(player)
	profiles[player] = nil
	loaded[player] = nil
end

function DataService.reset(player: Player)
	profiles[player] = defaults()
	return profiles[player]
end

function DataService.start()
	task.spawn(function()
		while true do
			task.wait(AUTOSAVE)
			for _, p in Players:GetPlayers() do
				task.spawn(DataService.save, p)
			end
		end
	end)
	game:BindToClose(function()
		if RunService:IsStudio() and not store then
			return
		end
		local threads = 0
		for _, p in Players:GetPlayers() do
			threads += 1
			task.spawn(function()
				DataService.save(p)
				threads -= 1
			end)
		end
		local t = os.clock()
		while threads > 0 and os.clock() - t < 20 do
			task.wait(0.1)
		end
	end)
end

return DataService

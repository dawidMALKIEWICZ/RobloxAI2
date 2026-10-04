local Players = game:GetService("Players")

local DataService = require(script.Parent.DataService)
local PlotService = require(script.Parent.PlotService)
local GameService = require(script.Parent.GameService)

DataService.start()
PlotService.start()
GameService.start()

Players.PlayerAdded:Connect(GameService.playerAdded)
Players.PlayerRemoving:Connect(GameService.playerRemoving)
for _, player in Players:GetPlayers() do
	task.spawn(GameService.playerAdded, player)
end

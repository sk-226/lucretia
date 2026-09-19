-- Keep the original order.
local function unique(items)
  local seen, result = {}, {}
  for _, item in ipairs(items) do
    if not seen[item] then
      seen[item] = true
      result[#result + 1] = item
    end
  end
  return result
end

local names = { "ink", "paper", "ink" }
local result = unique(names)
assert(#result == 2)
print(table.concat(result, ", "))

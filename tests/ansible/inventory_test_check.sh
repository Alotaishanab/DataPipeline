#!/bin/bash

echo "🔍 Checking for inventory at ../../ansible/inventories/inventory.json..."

INVENTORY_FILE="../../ansible/inventories/inventory.json"

if [ ! -f "$INVENTORY_FILE" ]; then
  echo "❌ Inventory file not found at $INVENTORY_FILE"
  exit 1
fi

echo "✅ Inventory file exists."

# Quick keyword checks
KEYWORDS=("worker1" "worker2" "localhost" "worker_inventory")

for KEY in "${KEYWORDS[@]}"; do
  if grep -q "$KEY" "$INVENTORY_FILE"; then
    echo "✅ Found '$KEY' in inventory."
  else
    echo "⚠️  Warning: '$KEY' not found in inventory."
  fi
done

echo "📦 Inventory basic check completed."

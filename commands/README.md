# Command reference data

The public repository includes `example_commands.json` with a small number of generic sample commands for demonstration. The **private** `commands.json` file derived from a workplace workbook is **not distributed in GitHub** and is ignored by Git.

PocketDesk loads `commands.json` if you have placed one locally. Otherwise, it falls back to `example_commands.json`. Do not publish workplace credentials, infrastructure inventories, production identifiers or confidential command packs.

You can create commands inside PocketDesk using **Commands → + New**. These are stored in `%APPDATA%\PocketDesk\data.json` and are also excluded from Git. Commands are copied, **not executed**.

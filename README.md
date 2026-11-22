# Ask your spreadsheet

A small MCP server that lets an AI assistant answer questions about a sales spreadsheet in plain English.

Ask "Which channel made the most money in August?" and the assistant looks the numbers up itself. The code does the maths, exactly; the AI only writes the answer. It's the working example behind my post [Want to build something with AI? Build your own MCP server, for free](https://lohkaixiang.com/blog/build-yourself-an-mcp-server).

## What it can do

Three abilities, all read-only:

| Ability | What it does |
|---|---|
| `describe_sheet` | Shows the columns, which ones hold numbers, and the values in each text column |
| `total` | Adds up a number column exactly, optionally split by a text column and filtered (e.g. one month or one region) |
| `top` | Ranks the values of a text column by a number column, highest first |

It ships with `sample_sales.csv`, a made-up quarter of sales for a small homeware shop, so you can try it straight away.

## Run it

Needs Python 3.10+.

```bash
pip install "mcp[cli]>=2"
python server.py
```

Then add it to an AI assistant that supports MCP. For Claude Desktop, add this to its config file and restart it:

```json
{
  "mcpServers": {
    "ask-your-spreadsheet": {
      "command": "python",
      "args": ["/full/path/to/server.py"]
    }
  }
}
```

To use your own data, export a sheet as CSV and point the server at it:

```json
"env": { "SHEET_PATH": "/full/path/to/your-sales.csv" }
```

## Questions to try

- What's in this spreadsheet?
- What was total revenue last quarter, by channel?
- Which three products sold the most in London?
- How did orders in August compare with September?

## Why it's built this way

- **Code does the maths, AI does the words.** An AI that adds numbers up itself will eventually get one wrong and say it confidently. Here every figure comes from `total` or `top`.
- **Read-only.** It opens the file to read and nothing else. It can't change or delete anything.
- **One file, one job.** It only reaches the spreadsheet you point it at.
- **Clear descriptions.** Most of the work in an MCP server is describing each ability well enough that the assistant knows when to use it.

## Tests

```bash
pip install pytest anyio
python -m pytest -q
```

## Licence

MIT

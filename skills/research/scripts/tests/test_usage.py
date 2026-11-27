"""Self-check for usage.py: python3 tests/test_usage.py"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE = os.path.join(SCRIPTS, "usage.py")
A = "aaaaaaaa-0000-0000-0000-000000000001"  # research session, with a subagent
B = "bbbbbbbb-0000-0000-0000-000000000002"  # unrelated session


def msg(mid, model, usage, content=(), ts="2026-11-26T10:00:00Z"):
    return json.dumps({"type": "assistant", "timestamp": ts, "requestId": "r" + mid,
                       "message": {"id": mid, "model": model, "usage": usage, "content": list(content)}})


def write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(cfg, research, *args):
    r = subprocess.run([sys.executable, USAGE, research, "--json", *args], capture_output=True, text=True,
                       env={**os.environ, "CLAUDE_CONFIG_DIR": cfg})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def main():
    with tempfile.TemporaryDirectory() as d:
        proj = f"{d}/projects/-x"
        u = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 1_000_000,
             "cache_creation_input_tokens": 1_000_000, "cache_creation": {"ephemeral_1h_input_tokens": 400_000}}
        search = {"type": "tool_use", "name": "WebSearch", "input": {"query": "q"}}
        fetch = {"type": "tool_use", "name": "Bash", "input": {"command": "python3 s/fetch.py research/topic u"}}
        # one response logged as two lines (one per content block) must be counted once
        write(f"{proj}/{A}.jsonl", [msg("m1", "claude-opus-5-5", u, [search]),
                                    msg("m1", "claude-opus-5-5", u, [fetch]),
                                    msg("m2", "<synthetic>", u)])
        write(f"{proj}/{A}/subagents/agent-1.jsonl", [msg("s1", "claude-haiku-5-5", {"input_tokens": 1_000_000})])
        write(f"{proj}/{B}.jsonl", [msg("x1", "claude-opus-5-5", u, [{"type": "text", "text": "research/topic-v2"}])])
        os.makedirs(f"{d}/research/topic")

        # no Sessions line: guessed from the skill scripts run on research/topic
        out = run(d, f"{d}/research/topic")
        assert out["sessions_from"] == "guessed" and [s["session"] for s in out["sessions"]] == [A], out
        opus = out["models"]["claude-opus-5-5"]
        assert opus["input"] == 1_000_000 and opus["web_searches"] == 1, opus
        # opus 5.5: 1M in $4 + 0.6M 5-min writes $3 + 0.4M 1-hour writes $3.20 + 1M reads $0.20 + 0.1M out $2
        # + one search $0.01; haiku 5.5 subagent: 1M in, a prompt over 100K, at $0.50
        assert abs(opus["cost"] - 12.41) < 1e-6, opus
        assert out["cost_usd"] == 12.91 and out["sessions"][0]["subagents"] == 1, out

        # the Sessions line wins over the guess
        with open(f"{d}/research/topic/STATE.md", "w") as f:
            f.write(f"# State\n\n- Sessions: {B}\n")
        out = run(d, f"{d}/research/topic")
        assert out["sessions_from"] == "STATE.md" and [s["session"] for s in out["sessions"]] == [B], out
        assert out["cost_usd"] == 12.4, out

        # unknown model: tokens counted, no cost
        write(f"{proj}/{B}.jsonl", [msg("x2", "claude-future-9", {"input_tokens": 5})])
        out = run(d, f"{d}/research/topic")
        assert out["models"]["claude-future-9"]["unpriced"] == 1 and out["cost_usd"] == 0, out
    print("ok")


if __name__ == "__main__":
    main()

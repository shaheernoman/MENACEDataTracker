import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.ticker as ticker

# ── Colour helpers ─────────────────────────────────────────────────────────────

# Maps common colour names to hex so dots render correctly on the graph
COLOUR_MAP = {
    "red":    "#c0392b",
    "blue":   "#1a5276",
    "green":  "#1a7a3a",
    "yellow": "#d4ac0d",
    "orange": "#e67e22",
    "pink":   "#c9417a",
    "purple": "#7d3c98",
    "white":  "#cccccc",
    "black":  "#222222",
    "brown":  "#7b4f2a",
    "grey":   "#7f8c8d",
    "gray":   "#7f8c8d",
    "cyan":   "#148a8a",
    "lime":   "#5dbb36",
    "gold":   "#c8a800",
    "silver": "#999999",
    "maroon": "#7b1a1a",
    "navy":   "#1a237e",
    "teal":   "#117a65",
    "violet": "#6a0dad",
}

def resolve_colour(name: str) -> str:
    """Return a hex colour for a given name, or a fallback."""
    key = name.strip().lower()
    if key in COLOUR_MAP:
        return COLOUR_MAP[key]
    # Try to validate as a direct hex / tk colour name
    try:
        root_test = tk.Tk()
        root_test.withdraw()
        root_test.winfo_rgb(key)
        root_test.destroy()
        return key
    except Exception:
        pass
    return "#888888"  # fallback grey

# ── App ────────────────────────────────────────────────────────────────────────

class MenaceLogger:
    PAPER      = "#f5f0e8"
    INK        = "#1a1209"
    INK_LIGHT  = "#7a6a50"
    RED_LINE   = "#c0392b"
    FONT_MONO  = ("Courier New", 10)
    FONT_TITLE = ("Courier New", 13, "bold")

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MENACE — Data Logger")
        self.root.configure(bg=self.PAPER)
        self.root.resizable(True, True)
        self.root.minsize(720, 580)

        # ── Data ──────────────────────────────────────────────────────────
        self.games: list[dict] = []   # {type, score, colour}
        self.bead_colours: list[str] = []   # user-defined colours
        self.selected_colour = tk.StringVar(value="")

        self._build_ui()
        self._refresh_graph()

    # ──────────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=self.PAPER)
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(hdr, text="MENACE — DATA LOGGER",
                 font=("Courier New", 15, "bold"),
                 bg=self.PAPER, fg=self.INK).pack()
        tk.Label(hdr, text="Machine Educable Noughts & Crosses Engine  ·  MENACE plays: O (Noughts)",
                 font=("Courier New", 9), bg=self.PAPER, fg=self.INK_LIGHT).pack()
        tk.Label(hdr, text="Score = 3×Wins − Losses − Draws",
                 font=("Courier New", 9, "italic"), bg=self.PAPER, fg=self.INK_LIGHT).pack()

        sep = tk.Frame(self.root, height=2, bg=self.INK)
        sep.pack(fill="x", padx=20, pady=8)

        # ── Main layout: left panel + graph ──────────────────────────────
        body = tk.Frame(self.root, bg=self.PAPER)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        left = tk.Frame(body, bg=self.PAPER, width=210)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=self.PAPER)
        right.pack(side="left", fill="both", expand=True)

        self._build_left_panel(left)
        self._build_graph(right)

        # ── Status bar ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready — record your first game.")
        sb = tk.Label(self.root, textvariable=self.status_var,
                      font=("Courier New", 9), bg=self.INK, fg=self.PAPER,
                      anchor="w", padx=10, pady=3)
        sb.pack(fill="x", side="bottom")

    def _build_left_panel(self, parent):
        # ── Stats ─────────────────────────────────────────────────────────
        stats_frame = tk.LabelFrame(parent, text=" STATISTICS ",
                                    font=self.FONT_MONO, bg=self.PAPER, fg=self.INK,
                                    bd=1, relief="solid")
        stats_frame.pack(fill="x", pady=(0, 10))

        self.stat_vars = {}
        for label, key, colour in [
            ("Games",   "games",  self.INK),
            ("Wins",    "wins",   "#1a4a2a"),
            ("Losses",  "losses", "#6b1a1a"),
            ("Draws",   "draws",  "#1a2a4a"),
            ("Score",   "score",  "#5a3000"),
        ]:
            row = tk.Frame(stats_frame, bg=self.PAPER)
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text=f"{label}:", font=self.FONT_MONO,
                     bg=self.PAPER, fg=self.INK_LIGHT, width=8, anchor="w").pack(side="left")
            var = tk.StringVar(value="0")
            tk.Label(row, textvariable=var, font=("Courier New", 12, "bold"),
                     bg=self.PAPER, fg=colour, anchor="e").pack(side="right")
            self.stat_vars[key] = var

        # ── Bead Colour Selector ──────────────────────────────────────────
        colour_frame = tk.LabelFrame(parent, text=" BEAD COLOUR ",
                                     font=self.FONT_MONO, bg=self.PAPER, fg=self.INK,
                                     bd=1, relief="solid")
        colour_frame.pack(fill="x", pady=(0, 10))

        tk.Label(colour_frame,
                 text="Select the colour MENACE\nplayed first on:",
                 font=("Courier New", 9), bg=self.PAPER, fg=self.INK_LIGHT,
                 justify="left").pack(anchor="w", padx=8, pady=(4, 2))

        self.colour_listbox_frame = tk.Frame(colour_frame, bg=self.PAPER)
        self.colour_listbox_frame.pack(fill="x", padx=8, pady=(0, 4))

        # Colour radio buttons live here (rebuilt when colours change)
        self.colour_radios_frame = tk.Frame(colour_frame, bg=self.PAPER)
        self.colour_radios_frame.pack(fill="x", padx=8, pady=(0, 4))

        # None option
        tk.Radiobutton(self.colour_radios_frame, text="— not recorded —",
                       variable=self.selected_colour, value="",
                       font=("Courier New", 9), bg=self.PAPER, fg=self.INK_LIGHT,
                       activebackground=self.PAPER, selectcolor=self.PAPER
                       ).pack(anchor="w")

        # Manage colours buttons
        btn_row = tk.Frame(colour_frame, bg=self.PAPER)
        btn_row.pack(fill="x", padx=8, pady=(2, 6))
        self._btn(btn_row, "＋ Add Colour", self._add_colour,
                  bg="#e8e0cc", fg=self.INK, width=11).pack(side="left", padx=(0,4))
        self._btn(btn_row, "✕ Remove", self._remove_colour,
                  bg="#e8e0cc", fg="#6b1a1a", width=9).pack(side="left")

        # ── Record Result ─────────────────────────────────────────────────
        rec_frame = tk.LabelFrame(parent, text=" RECORD RESULT ",
                                  font=self.FONT_MONO, bg=self.PAPER, fg=self.INK,
                                  bd=1, relief="solid")
        rec_frame.pack(fill="x", pady=(0, 10))

        self._btn(rec_frame, "✓  MENACE WINS (O)",
                  lambda: self._record("WIN"),
                  bg="#1a4a2a", fg="white", width=22).pack(fill="x", padx=8, pady=(8,3))
        self._btn(rec_frame, "✗  MENACE LOSES",
                  lambda: self._record("LOSS"),
                  bg="#6b1a1a", fg="white", width=22).pack(fill="x", padx=8, pady=3)
        self._btn(rec_frame, "=  DRAW",
                  lambda: self._record("DRAW"),
                  bg="#1a2a4a", fg="white", width=22).pack(fill="x", padx=8, pady=(3,8))

        # ── Undo / Reset ──────────────────────────────────────────────────
        ctrl_frame = tk.Frame(parent, bg=self.PAPER)
        ctrl_frame.pack(fill="x")
        self._btn(ctrl_frame, "↩ Undo", self._undo,
                  bg=self.PAPER, fg=self.INK_LIGHT).pack(side="left", padx=(0,6))
        self._btn(ctrl_frame, "⊘ Reset All", self._reset,
                  bg=self.PAPER, fg="#999").pack(side="left")

        # ── Export ────────────────────────────────────────────────────────
        exp_frame = tk.Frame(parent, bg=self.PAPER)
        exp_frame.pack(fill="x", pady=(6, 0))
        self._btn(exp_frame, "↓ Export to CSV", self._export_csv,
                  bg="#2a3a5a", fg="white", width=22).pack(fill="x")

        # ── Last result label ─────────────────────────────────────────────
        self.last_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.last_var,
                 font=("Courier New", 10, "bold"),
                 bg=self.PAPER, fg="#c0392b").pack(pady=(10,0))

    def _build_graph(self, parent):
        self.fig, self.ax = plt.subplots(figsize=(6, 4.2), dpi=100)
        self.fig.patch.set_facecolor(self.PAPER)

        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widget.mpl_connect("motion_notify_event", self._on_hover)

        self.annot = self.ax.annotate(
            "", xy=(0,0), xytext=(10,10), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc=self.INK, ec="none"),
            color=self.PAPER, fontsize=8, fontfamily="monospace",
            visible=False
        )

    # ──────────────────────────────────────────────────────────────────────
    # Colour management
    # ──────────────────────────────────────────────────────────────────────

    def _add_colour(self):
        name = simpledialog.askstring(
            "Add Bead Colour",
            "Enter colour name (e.g. red, blue, green, #ff6600):",
            parent=self.root
        )
        if not name:
            return
        name = name.strip()
        if name.lower() in [c.lower() for c in self.bead_colours]:
            messagebox.showinfo("Duplicate", f'"{name}" is already in the list.')
            return
        self.bead_colours.append(name)
        self._rebuild_colour_radios()

    def _remove_colour(self):
        current = self.selected_colour.get()
        if not current:
            messagebox.showinfo("Remove Colour", "Select a colour to remove first.")
            return
        self.bead_colours = [c for c in self.bead_colours if c != current]
        self.selected_colour.set("")
        self._rebuild_colour_radios()

    def _rebuild_colour_radios(self):
        for w in self.colour_radios_frame.winfo_children():
            w.destroy()

        tk.Radiobutton(self.colour_radios_frame, text="— not recorded —",
                       variable=self.selected_colour, value="",
                       font=("Courier New", 9), bg=self.PAPER, fg=self.INK_LIGHT,
                       activebackground=self.PAPER, selectcolor=self.PAPER
                       ).pack(anchor="w")

        for cname in self.bead_colours:
            hex_col = resolve_colour(cname)
            # Small colour swatch label + radio
            row = tk.Frame(self.colour_radios_frame, bg=self.PAPER)
            row.pack(anchor="w", fill="x")

            swatch = tk.Label(row, text="  ", bg=hex_col,
                              relief="solid", bd=1, width=2)
            swatch.pack(side="left", padx=(2,4), pady=1)

            rb = tk.Radiobutton(row, text=cname.title(),
                                variable=self.selected_colour, value=cname,
                                font=("Courier New", 9), bg=self.PAPER, fg=self.INK,
                                activebackground=self.PAPER, selectcolor=self.PAPER)
            rb.pack(side="left")

    # ──────────────────────────────────────────────────────────────────────
    # Data actions
    # ──────────────────────────────────────────────────────────────────────

    def _record(self, result_type: str):
        prev_score = self.games[-1]["score"] if self.games else 0
        delta = {"WIN": 3, "LOSS": -1, "DRAW": -1}[result_type]
        colour = self.selected_colour.get()
        self.games.append({
            "type":   result_type,
            "score":  prev_score + delta,
            "colour": colour,
        })
        self._update_stats()
        self._refresh_graph()
        labels = {"WIN": "✓ MENACE WINS", "LOSS": "✗ MENACE LOSES", "DRAW": "= DRAW"}
        col_note = f"  [{colour}]" if colour else ""
        self.last_var.set(f"Last: {labels[result_type]}{col_note}")
        self.status_var.set(
            f"Game {len(self.games)} recorded: {result_type}"
            + (f" | Bead: {colour}" if colour else "")
        )

    def _undo(self):
        if not self.games:
            return
        removed = self.games.pop()
        self._update_stats()
        self._refresh_graph()
        self.last_var.set(f"Undone: game {len(self.games)+1} ({removed['type']})")
        self.status_var.set(f"Undo — removed game {len(self.games)+1}.")

    def _reset(self):
        if not self.games:
            return
        if not messagebox.askyesno("Reset", "Clear all recorded games?"):
            return
        self.games.clear()
        self._update_stats()
        self._refresh_graph()
        self.last_var.set("")
        self.status_var.set("Reset — all data cleared.")

    # ──────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────

    def _update_stats(self):
        wins   = sum(1 for g in self.games if g["type"] == "WIN")
        losses = sum(1 for g in self.games if g["type"] == "LOSS")
        draws  = sum(1 for g in self.games if g["type"] == "DRAW")
        score  = self.games[-1]["score"] if self.games else 0

        self.stat_vars["games"].set(str(len(self.games)))
        self.stat_vars["wins"].set(str(wins))
        self.stat_vars["losses"].set(str(losses))
        self.stat_vars["draws"].set(str(draws))
        self.stat_vars["score"].set(f"{score:+d}" if self.games else "0")

    # ──────────────────────────────────────────────────────────────────────
    # Graph
    # ──────────────────────────────────────────────────────────────────────

    def _refresh_graph(self):
        ax = self.ax
        ax.clear()
        ax.set_facecolor(self.PAPER)

        # Build score series: starts at (0,0)
        xs = list(range(len(self.games) + 1))
        ys = [0] + [g["score"] for g in self.games]

        # ── Grid ──────────────────────────────────────────────────────────
        ax.grid(True, which="major", color="#c8b89a", linewidth=0.6, linestyle="-")
        ax.grid(True, which="minor", color="#ddd0b8", linewidth=0.3, linestyle="-")
        ax.minorticks_on()
        ax.set_axisbelow(True)

        # ── Zero line ─────────────────────────────────────────────────────
        ax.axhline(0, color="#a08060", linewidth=0.8, linestyle="--", alpha=0.6, zorder=1)

        # ── Line plot ─────────────────────────────────────────────────────
        if len(xs) > 1:
            ax.plot(xs, ys, color=self.RED_LINE, linewidth=1.6,
                    zorder=2, solid_capstyle="round")

        # ── Scatter dots coloured by bead colour ──────────────────────────
        self._scatter_pts = []   # for hover
        if self.games:
            for i, game in enumerate(self.games):
                gx = i + 1
                gy = game["score"]
                cname = game["colour"]
                hex_col = resolve_colour(cname) if cname else None

                # Dot fill = bead colour if set, else type-based fallback
                if hex_col:
                    face = hex_col
                else:
                    face = {"WIN": "#1a4a2a", "LOSS": "#6b1a1a", "DRAW": "#1a2a4a"}[game["type"]]

                sc = ax.scatter(gx, gy, s=38, color=face,
                                edgecolors="#f5f0e8", linewidths=0.8, zorder=3)
                self._scatter_pts.append((gx, gy, game))

        # ── Legend for bead colours ───────────────────────────────────────
        seen = {}
        for game in self.games:
            c = game["colour"]
            if c and c not in seen:
                seen[c] = resolve_colour(c)
        if seen:
            patches = [mpatches.Patch(color=hex_, label=name.title())
                       for name, hex_ in seen.items()]
            ax.legend(handles=patches, loc="upper left",
                      fontsize=7, framealpha=0.7,
                      facecolor=self.PAPER, edgecolor="#c8b89a")

        # ── Axes styling ──────────────────────────────────────────────────
        ax.set_xlabel("Number of games", fontfamily="monospace", fontsize=9, color=self.INK)
        ax.set_ylabel("Score  (3×W − L − D)", fontfamily="monospace", fontsize=9, color=self.INK)
        ax.tick_params(labelsize=8, colors=self.INK)
        for spine in ax.spines.values():
            spine.set_edgecolor("#a08060")
            spine.set_linewidth(1.2)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        if not self.games:
            ax.text(0.5, 0.5, "Record the first game →",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    fontfamily="monospace", fontsize=10,
                    color="#a08060", style="italic")

        self.fig.tight_layout()
        self.canvas_widget.draw()

    # ──────────────────────────────────────────────────────────────────────
    # Hover tooltip
    # ──────────────────────────────────────────────────────────────────────

    def _on_hover(self, event):
        if event.inaxes != self.ax or not hasattr(self, "_scatter_pts"):
            self.annot.set_visible(False)
            self.canvas_widget.draw_idle()
            return

        found = None
        best  = 0.6   # axis-unit radius threshold
        for (gx, gy, game) in self._scatter_pts:
            if event.xdata is None or event.ydata is None:
                continue
            dist = ((event.xdata - gx)**2 + (event.ydata - gy)**2) ** 0.5
            if dist < best:
                best = dist
                found = (gx, gy, game)

        if found:
            gx, gy, game = found
            cname = game["colour"] or "—"
            type_sym = {"WIN": "W ✓", "LOSS": "L ✗", "DRAW": "D ="}[game["type"]]
            score_str = f"{game['score']:+d}" if game["score"] != 0 else "0"
            label = f"Game {gx}  {type_sym}\nBead: {cname}\nScore: {score_str}"
            self.annot.set_text(label)
            self.annot.xy = (gx, gy)
            self.annot.set_visible(True)
        else:
            self.annot.set_visible(False)

        self.canvas_widget.draw_idle()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _btn(self, parent, text, cmd, bg, fg, width=None):
        kw = dict(text=text, command=cmd, bg=bg, fg=fg,
                  font=("Courier New", 9, "bold"),
                  relief="flat", bd=0, padx=8, pady=5,
                  cursor="hand2", activebackground=bg, activeforeground=fg)
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)


    def _export_csv(self):
        if not self.games:
            messagebox.showinfo("Export", "No games recorded yet — nothing to export.")
            return

        default_name = f"menace_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            title="Export MENACE Results",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return  # user cancelled

        wins   = sum(1 for g in self.games if g["type"] == "WIN")
        losses = sum(1 for g in self.games if g["type"] == "LOSS")
        draws  = sum(1 for g in self.games if g["type"] == "DRAW")
        final_score = self.games[-1]["score"] if self.games else 0

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Header metadata
                writer.writerow(["MENACE Data Logger Export"])
                writer.writerow(["Exported", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(["MENACE plays", "O (Noughts)"])
                writer.writerow(["Score formula", "3 x Wins - Losses - Draws"])
                writer.writerow([])

                # Summary
                writer.writerow(["SUMMARY"])
                writer.writerow(["Total Games", len(self.games)])
                writer.writerow(["Wins",        wins])
                writer.writerow(["Losses",      losses])
                writer.writerow(["Draws",       draws])
                writer.writerow(["Final Score", final_score])
                writer.writerow([])

                # Per-game data
                writer.writerow(["GAME LOG"])
                writer.writerow(["Game", "Result", "Bead Colour", "Score Delta", "Running Score"])
                for i, game in enumerate(self.games, start=1):
                    delta = {"WIN": "+3", "LOSS": "-1", "DRAW": "-1"}[game["type"]]
                    writer.writerow([
                        i,
                        game["type"],
                        game["colour"] if game["colour"] else "—",
                        delta,
                        game["score"],
                    ])

            self.status_var.set(f"Exported {len(self.games)} games to: {filepath}")
            messagebox.showinfo("Export Successful", f"Saved {len(self.games)} games to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = MenaceLogger(root)
    root.mainloop()

if __name__ == "__main__":
    main()
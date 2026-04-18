"""Internationalisation string table.

Call ``set_language(lang)`` once at application startup (before any widget
is created).  ``t(key)`` then returns the translated string for the active
language, falling back to English when a key is absent in the target
language.

Supported language codes: ``"en"`` (default), ``"it"`` (Italiano).
"""

from __future__ import annotations

_lang: str = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Skills
        "skill.stamina":    "Stamina",
        "skill.resilience": "Resilience",
        "skill.pace":       "Pace",
        "skill.agility":    "Agility",
        "skill.aggression": "Aggression",
        "skill.flair":      "Flair",
        "skill.passing":    "Passing",
        "skill.shooting":   "Shooting",
        "skill.tackling":   "Tackling",
        "skill.keeping":    "Keeping",
        # Positions
        "pos.gk":  "GK",
        "pos.def": "DEF",
        "pos.mid": "MID",
        "pos.fwd": "FWD",
        # Tabs
        "tab.core":   "Core",
        "tab.skills": "Skills",
        "tab.status": "Status",
        "tab.season": "Season",
        "tab.career": "Career",
        # Tree columns (main player list)
        "col.id":    "ID",
        "col.name":  "Name",
        "col.age":   "Age",
        "col.pos":   "Pos",
        "col.team":  "Team",
        "col.skill": "Skill",
        "col.warn":  "\u26a0",
        "col.mkt":   "Mkt",
        "col.goals": "Goals",
        # Squad Analyst column overrides
        "col.sa.id":    "Tm",
        "col.sa.age":   "AvgAge",
        "col.sa.pos":   "Size",
        "col.sa.team":  "GK\u00b7DEF\u00b7MID\u00b7FWD",
        "col.sa.skill": "AvgSkl",
        # Identity header field labels
        "field.player_id": "Player #",
        "field.name":      "Name",
        "field.seed":      "Seed",
        # Core tab field labels
        "field.age":        "Age:",
        "field.position":   "Position:",
        "field.division":   "Division:",
        "field.team_index": "Team Index:",
        "field.height":     "Height (cm):",
        "field.weight":     "Weight (kg):",
        # Status tab field labels
        "field.injury_weeks":         "Injury Weeks:",
        "field.disciplinary":         "Disciplinary:",
        "field.morale":               "Morale:",
        "field.value":                "Value:",
        "field.weeks_since_transfer": "Wks Since Transfer:",
        # Season tab field labels
        "field.injuries_this_year":  "Injuries This Yr:",
        "field.injuries_last_year":  "Injuries Last Yr:",
        "field.dsp_pts_this_year":   "Dsp.Pts. This Yr:",
        "field.dsp_pts_last_year":   "Dsp.Pts. Last Yr:",
        "field.goals_this_year":     "Goals This Yr:",
        "field.goals_last_year":     "Goals Last Yr:",
        "field.matches_this_year":   "Matches This Yr:",
        "field.matches_last_year":   "Matches Last Yr:",
        # Career tab field labels
        "field.div1_years":     "Div1 Years:",
        "field.div2_years":     "Div2 Years:",
        "field.div3_years":     "Div3 Years:",
        "field.div4_years":     "Div4 Years:",
        "field.int_years":      "Int Years:",
        "field.contract_years": "Contract Yrs:",
        # Misc status-tab labels
        "label.weakness":          "Weakness:",
        "label.none":              "none",
        "label.warnings_disabled": "(warnings disabled in Preferences)",
        # Toolbar labels
        "toolbar.save": "SAVE:",
        "toolbar.view": "VIEW:",
        # View combo / View menu entries
        "view.all":         "All Players",
        "view.free_agents": "Free Agents",
        "view.young":       "\u2014 Young Talents (\u226421)",
        "view.scorers":     "\u2014 Top Scorers",
        "view.squad":       "\u2014 Squad Analyst (all teams)",
        "view.top11_442":   "\u2014 Top 11 (4-4-2)",
        "view.top11_433":   "\u2014 Top 11 (4-3-3)",
        "view.young_xi":    "\u2014 Young XI (\u226421)",
        "view.fa_xi":       "\u2014 Free-Agent XI",
        # Menu bar cascade labels
        "menu.file":  "File",
        "menu.edit":  "Edit",
        "menu.view":  "View",
        "menu.tools": "Tools",
        "menu.help":  "Help",
        # File menu items
        "menu.file.open_save":    "Open Save Disk\u2026",
        "menu.file.open_game":    "Open Game Disk\u2026",
        "menu.file.recent":       "Open Recent",
        "menu.file.save":         "Save",
        "menu.file.save_as":      "Save As\u2026",
        "menu.file.export":       "Export Players\u2026",
        "menu.file.quit":         "Quit",
        "menu.file.recent_empty": "(empty)",
        "menu.file.clear_recent": "Clear Recent",
        # Edit menu items
        "menu.edit.apply":  "Apply Changes",
        "menu.edit.revert": "Revert Player",
        "menu.edit.find":   "Find Player\u2026",
        # View menu items
        "menu.view.all":         "All Players",
        "menu.view.free_agents": "Free Agents",
        "menu.view.young":       "Young Talents (\u226421)",
        "menu.view.scorers":     "Top Scorers",
        "menu.view.squad":       "Squad Analyst (all teams)",
        "menu.view.best_xi":     "Best XI",
        # Tools menu items
        "menu.tools.career":    "Career Tracker\u2026",
        "menu.tools.workbench": "Byte Workbench\u2026",
        "menu.tools.lineup":    "Line-up Coach (BETA)\u2026",
        "menu.tools.compare":   "Compare Players\u2026",
        "menu.tools.tactic":    "Tactic Editor\u2026",
        # Help menu items
        "menu.help.search":  "Find in Help\u2026",
        "menu.help.manual":  "Open Manual",
        "menu.help.updates": "Check for Updates\u2026",
        "menu.help.prefs":   "Preferences\u2026",
        "menu.help.about":   "About",
        # About dialog
        "menu.about.title": "About Player Manager Toolkit",
        # Context menu (right-click on player)
        "ctx.send_compare": "Send to Compare\u2026",
        "ctx.copy_id":      "Copy ID #",
        # Search bar
        "label.filter": "Filter:",
        # Status bar
        "status.open_prompt":  "Open a save disk to begin.",
        "status.no_game_disk": "No game disk",
        # Sticky footer buttons
        "btn.apply":  "APPLY",
        "btn.revert": "REVERT",
        # Dialog titles / messages
        "dlg.unsaved_title": "Unsaved changes",
        "dlg.unsaved_msg":   "Save current changes before opening a new ADF?",
        "dlg.quit_msg":      ("You have unsaved changes to the ADF."
                              "\n\nSave before quitting?"),
        # Welcome dialog
        "welcome.title":          "Welcome",
        "welcome.banner":         "WELCOME",
        "welcome.show_at_launch": "Show this at every launch",
        "welcome.btn_go":         "  OK, LET'S GO  ",
        "welcome.box1_big":   "OPEN YOUR SAVE DISK",
        "welcome.box1_small": ("File \u2192 Open Save Disk\u2026"
                               " \u2014 browse and edit every player"),
        "welcome.box2_big":   "OPTIONAL: OPEN GAME DISK",
        "welcome.box2_small": ("File \u2192 Open Game Disk\u2026"
                               " \u2014 unlocks player names"),
        "welcome.box3_big":   "BROWSE, EDIT, SAVE",
        "welcome.box3_small": ("Pick a VIEW, click a player, tweak, save"
                               " (makes a .bak first)"),
        "welcome.box4_big":   "EXPLORE THE TOOLS MENU",
        "welcome.box4_small": ("Career Tracker \u00b7 Compare Players"
                               " \u00b7 Line-up Coach \u00b7 Byte Workbench"),
        "welcome.box5_big":   "NEED HELP?",
        "welcome.box5_small": "Tap the ? button in any window for in-app guidance",
        # Line-up Coach
        "lineup.title":         "Line-up Coach (BETA)",
        "lineup.header":        "Line-up Coach",
        "lineup.team":          "Team:",
        "lineup.whole_champ":   "\u2014 Whole championship",
        "lineup.formation":     "Formation:",
        "lineup.rank_all":      "\u2014 Rank all",
        "lineup.cross_pos":     "Allow cross-position",
        "lineup.include_inj":   "Include injured",
        "lineup.compute":       "Compute",
        "lineup.form_ranking":  "Formation ranking",
        "lineup.reassign":      "Reassignment suggestions",
        "lineup.click_compute": "Click Compute to generate a suggested XI.",
        "lineup.reserves":      "\u2014 Reserves \u2014",
        "lineup.col.form":      "Formation",
        "lineup.col.comp":      "Composite",
        "lineup.col.skill":     "Skill",
        "lineup.col.fit":       "Fit%",
        "lineup.col.role":      "Role",
        "lineup.col.pid":       "ID",
        "lineup.col.name":      "Name",
        "lineup.col.age":       "Age",
        "lineup.col.team":      "Team",
        "lineup.col.nominal":   "Nominal",
        "lineup.col.suggested": "Suggested",
        "lineup.col.gap":       "Gap",
        "lineup.col.player":    "Player",
        # Career Tracker
        "career.title":      "Career Tracker",
        "career.slot_a":     "Slot A:",
        "career.slot_b":     "Slot B:",
        "career.same_adf":   "(same ADF)",
        "career.load_b":     "Load side-B ADF...",
        "career.reset_b":    "Reset to same ADF",
        "career.team_only":  "Team changes only",
        "career.compare":    "Compare",
        "career.col.id":     "ID",
        "career.col.name":   "Name",
        "career.col.age_a":  "Age A",
        "career.col.age_b":  "Age B",
        "career.col.skill_a": "Skill A",
        "career.col.skill_b": "Skill B",
        "career.col.delta":  "\u0394Skill",
        "career.col.team_a": "Team A",
        "career.col.team_b": "Team B",
        "career.ready":      "Ready.",
        # Compare Players
        "compare.title":       "Compare Players",
        "compare.header":      "COMPARE PLAYERS",
        "compare.team":        "Team",
        "compare.player":      "Player",
        "compare.free_agents": "\u2605 Free Agents",
        "compare.select":      "Select two players to compare.",
        "compare.done":        "DONE",
        # Preferences dialog
        "pref.title":       "Preferences",
        "pref.on_launch":   "On launch",
        "pref.splash":      "Show splash screen",
        "pref.welcome":     "Show welcome screen",
        "pref.auto_save":   "Auto-open last save disk",
        "pref.auto_game":   "Auto-open last game disk",
        "pref.path_none":   "(none recorded yet)",
        "pref.path_missing": "\u26a0 missing: ",
        "pref.defaults":    "Defaults",
        "pref.default_view": "Default view when opening a save disk:",
        "pref.first_team":  "(first team in save)",
        "pref.default_form": "Default formation (Line-up Coach):",
        "pref.theme":       "Colour theme:",
        "pref.theme_retro": "Retro (Amiga navy / amber / cyan)",
        "pref.theme_light": "Light (accessible high-contrast)",
        "pref.system_font": "Use system font instead of retro Topaz",
        "pref.font_note":   "Font and theme changes take effect on next launch.",
        "pref.skill_warn":  "Flag players whose essential skills are below 100 (\u26a0)",
        "pref.skill_warn_note": (
            "Warns e.g. a GK with low keeping, a DEF with low tackling, "
            "a FWD with low\npace. Applies immediately to the player list "
            "and Status tab."
        ),
        "pref.updates":     "Updates",
        "pref.update_freq": "Automatic update checks:",
        "pref.upd_disabled": "Disabled",
        "pref.upd_daily":   "Daily",
        "pref.upd_weekly":  "Weekly",
        "pref.upd_note": (
            'A "New version available" banner appears next to the title\n'
            "when a newer release is found on GitHub. No data is sent."
        ),
        "pref.language":  "Language",
        "pref.lang_note": "Language changes take effect on next launch.",
        "btn.cancel": "Cancel",
        "btn.save":   "Save",
    },

    "it": {
        # Skills
        "skill.stamina":    "Stamina",
        "skill.resilience": "Resistenza",
        "skill.pace":       "Velocita'",
        "skill.agility":    "Agilita'",
        "skill.aggression": "Aggressivita'",
        "skill.flair":      "Estro",
        "skill.passing":    "Passaggio",
        "skill.shooting":   "Tiro",
        "skill.tackling":   "Contrasto",
        "skill.keeping":    "Parata",
        # Positions
        "pos.gk":  "Port.",
        "pos.def": "Dif.",
        "pos.mid": "Cen.",
        "pos.fwd": "Att.",
        # Tabs
        "tab.core":   "Dati",
        "tab.skills": "Abilita'",
        "tab.status": "Stato",
        "tab.season": "Stagione",
        "tab.career": "Storia",
        # Tree columns (main player list)
        "col.id":    "ID",
        "col.name":  "Nome",
        "col.age":   "Eta'",
        "col.pos":   "Ruolo",
        "col.team":  "Squadra",
        "col.skill": "Abil.",
        "col.warn":  "\u26a0",
        "col.mkt":   "Mkt",
        "col.goals": "Gol",
        # Squad Analyst column overrides
        "col.sa.id":    "Sq",
        "col.sa.age":   "EtaMedia",
        "col.sa.pos":   "Rosa",
        "col.sa.team":  "Port\u00b7Dif\u00b7Cen\u00b7Att",
        "col.sa.skill": "AbilMedia",
        # Identity header field labels
        "field.player_id": "Giocatore #",
        "field.name":      "Nome",
        "field.seed":      "Seed",
        # Core tab field labels
        "field.age":        "Eta':",
        "field.position":   "Ruolo:",
        "field.division":   "Divisione:",
        "field.team_index": "Ind. Squadra:",
        "field.height":     "Altezza (cm):",
        "field.weight":     "Peso (kg):",
        # Status tab field labels
        "field.injury_weeks":         "Sett. Infortuni:",
        "field.disciplinary":         "Disciplinare:",
        "field.morale":               "Morale:",
        "field.value":                "Valore:",
        "field.weeks_since_transfer": "Sett. dal Trasf.:",
        # Season tab field labels
        "field.injuries_this_year":  "Infortuni Quest'Anno:",
        "field.injuries_last_year":  "Infortuni Anno Scorso:",
        "field.dsp_pts_this_year":   "Punti Disc. Quest'Anno:",
        "field.dsp_pts_last_year":   "Punti Disc. Anno Scorso:",
        "field.goals_this_year":     "Gol Quest'Anno:",
        "field.goals_last_year":     "Gol Anno Scorso:",
        "field.matches_this_year":   "Partite Quest'Anno:",
        "field.matches_last_year":   "Partite Anno Scorso:",
        # Career tab field labels
        "field.div1_years":     "Anni Div.1:",
        "field.div2_years":     "Anni Div.2:",
        "field.div3_years":     "Anni Div.3:",
        "field.div4_years":     "Anni Div.4:",
        "field.int_years":      "Anni Internaz.:",
        "field.contract_years": "Anni Contratto:",
        # Misc status-tab labels
        "label.weakness":          "Debolezza:",
        "label.none":              "nessuna",
        "label.warnings_disabled": "(avvisi disabilitati nelle Preferenze)",
        # Toolbar labels
        "toolbar.save": "SLOT:",
        "toolbar.view": "VISTA:",
        # View combo / View menu entries
        "view.all":         "Tutti i Giocatori",
        "view.free_agents": "Svincolati",
        "view.young":       "\u2014 Giovani Talenti (\u226421)",
        "view.scorers":     "\u2014 Capocannonieri",
        "view.squad":       "\u2014 Analisi Squadre",
        "view.top11_442":   "\u2014 Migliore XI (4-4-2)",
        "view.top11_433":   "\u2014 Migliore XI (4-3-3)",
        "view.young_xi":    "\u2014 XI Giovani (\u226421)",
        "view.fa_xi":       "\u2014 XI Svincolati",
        # Menu bar cascade labels
        "menu.file":  "File",
        "menu.edit":  "Modifica",
        "menu.view":  "Vista",
        "menu.tools": "Strumenti",
        "menu.help":  "Aiuto",
        # File menu items
        "menu.file.open_save":    "Apri Disco Partita\u2026",
        "menu.file.open_game":    "Apri Disco Gioco\u2026",
        "menu.file.recent":       "Recenti",
        "menu.file.save":         "Salva",
        "menu.file.save_as":      "Salva come\u2026",
        "menu.file.export":       "Esporta Giocatori\u2026",
        "menu.file.quit":         "Esci",
        "menu.file.recent_empty": "(vuoto)",
        "menu.file.clear_recent": "Cancella Recenti",
        # Edit menu items
        "menu.edit.apply":  "Applica Modifiche",
        "menu.edit.revert": "Annulla Modifiche",
        "menu.edit.find":   "Trova Giocatore\u2026",
        # View menu items
        "menu.view.all":         "Tutti i Giocatori",
        "menu.view.free_agents": "Svincolati",
        "menu.view.young":       "Giovani Talenti (\u226421)",
        "menu.view.scorers":     "Capocannonieri",
        "menu.view.squad":       "Analisi Squadre",
        "menu.view.best_xi":     "Migliore XI",
        # Tools menu items
        "menu.tools.career":    "Monitoraggio Carriera\u2026",
        "menu.tools.workbench": "Analisi Byte\u2026",
        "menu.tools.lineup":    "Allenatore (BETA)\u2026",
        "menu.tools.compare":   "Confronta Giocatori\u2026",
        "menu.tools.tactic":    "Editor Tattica\u2026",
        # Help menu items
        "menu.help.search":  "Cerca nella Guida\u2026",
        "menu.help.manual":  "Apri Manuale",
        "menu.help.updates": "Controlla Aggiornamenti\u2026",
        "menu.help.prefs":   "Preferenze\u2026",
        "menu.help.about":   "Informazioni",
        # About dialog
        "menu.about.title": "Informazioni su Player Manager Toolkit",
        # Context menu (right-click on player)
        "ctx.send_compare": "Invia a Confronto\u2026",
        "ctx.copy_id":      "Copia ID #",
        # Search bar
        "label.filter": "Filtro:",
        # Status bar
        "status.open_prompt":  "Apri un disco partita per iniziare.",
        "status.no_game_disk": "Nessun disco gioco",
        # Sticky footer buttons
        "btn.apply":  "APPLICA",
        "btn.revert": "RIPRISTINA",
        # Dialog titles / messages
        "dlg.unsaved_title": "Modifiche non salvate",
        "dlg.unsaved_msg":   "Salvare le modifiche prima di aprire un nuovo ADF?",
        "dlg.quit_msg":      ("Hai modifiche non salvate nell'ADF."
                              "\n\nSalvare prima di uscire?"),
        # Welcome dialog
        "welcome.title":          "Benvenuto",
        "welcome.banner":         "BENVENUTO",
        "welcome.show_at_launch": "Mostra ad ogni avvio",
        "welcome.btn_go":         "  ANDIAMO!  ",
        "welcome.box1_big":   "APRI IL DISCO PARTITA",
        "welcome.box1_small": ("File \u2192 Apri Disco Partita\u2026"
                               " \u2014 sfoglia e modifica ogni giocatore"),
        "welcome.box2_big":   "OPZIONALE: APRI IL DISCO GIOCO",
        "welcome.box2_small": ("File \u2192 Apri Disco Gioco\u2026"
                               " \u2014 sblocca i nomi dei giocatori"),
        "welcome.box3_big":   "SFOGLIA, MODIFICA, SALVA",
        "welcome.box3_small": ("Scegli una VISTA, clicca un giocatore,"
                               " modifica, salva (fa un .bak prima)"),
        "welcome.box4_big":   "ESPLORA IL MENU STRUMENTI",
        "welcome.box4_small": ("Monitoraggio Carriera \u00b7 Confronta Giocatori"
                               " \u00b7 Allenatore \u00b7 Analisi Byte"),
        "welcome.box5_big":   "HAI BISOGNO DI AIUTO?",
        "welcome.box5_small": "Tocca il pulsante ? per la guida in ogni finestra",
        # Line-up Coach
        "lineup.title":         "Allenatore (BETA)",
        "lineup.header":        "Allenatore",
        "lineup.team":          "Squadra:",
        "lineup.whole_champ":   "\u2014 Intero campionato",
        "lineup.formation":     "Formazione:",
        "lineup.rank_all":      "\u2014 Classifica tutte",
        "lineup.cross_pos":     "Permetti fuori ruolo",
        "lineup.include_inj":   "Includi infortunati",
        "lineup.compute":       "Calcola",
        "lineup.form_ranking":  "Classifica formazioni",
        "lineup.reassign":      "Suggerimenti cambio ruolo",
        "lineup.click_compute": "Clicca Calcola per generare un XI consigliato.",
        "lineup.reserves":      "\u2014 Riserve \u2014",
        "lineup.col.form":      "Formazione",
        "lineup.col.comp":      "Composito",
        "lineup.col.skill":     "Abil.",
        "lineup.col.fit":       "Adatt.%",
        "lineup.col.role":      "Ruolo",
        "lineup.col.pid":       "ID",
        "lineup.col.name":      "Nome",
        "lineup.col.age":       "Eta'",
        "lineup.col.team":      "Squadra",
        "lineup.col.nominal":   "Nominale",
        "lineup.col.suggested": "Suggerito",
        "lineup.col.gap":       "Diff.",
        "lineup.col.player":    "Giocatore",
        # Career Tracker
        "career.title":      "Monitoraggio Carriera",
        "career.slot_a":     "Slot A:",
        "career.slot_b":     "Slot B:",
        "career.same_adf":   "(stesso ADF)",
        "career.load_b":     "Carica ADF lato-B...",
        "career.reset_b":    "Ripristina stesso ADF",
        "career.team_only":  "Solo cambi squadra",
        "career.compare":    "Confronta",
        "career.col.id":     "ID",
        "career.col.name":   "Nome",
        "career.col.age_a":  "Eta' A",
        "career.col.age_b":  "Eta' B",
        "career.col.skill_a": "Abil. A",
        "career.col.skill_b": "Abil. B",
        "career.col.delta":  "\u0394Abil.",
        "career.col.team_a": "Squadra A",
        "career.col.team_b": "Squadra B",
        "career.ready":      "Pronto.",
        # Compare Players
        "compare.title":       "Confronta Giocatori",
        "compare.header":      "CONFRONTA GIOCATORI",
        "compare.team":        "Squadra",
        "compare.player":      "Giocatore",
        "compare.free_agents": "\u2605 Svincolati",
        "compare.select":      "Seleziona due giocatori da confrontare.",
        "compare.done":        "FATTO",
        # Preferences dialog
        "pref.title":       "Preferenze",
        "pref.on_launch":   "All'avvio",
        "pref.splash":      "Mostra schermata iniziale",
        "pref.welcome":     "Mostra schermata benvenuto",
        "pref.auto_save":   "Riapri ultimo disco partita",
        "pref.auto_game":   "Riapri ultimo disco gioco",
        "pref.path_none":   "(nessuno registrato)",
        "pref.path_missing": "\u26a0 mancante: ",
        "pref.defaults":    "Impostazioni",
        "pref.default_view": "Vista predefinita all'apertura del disco partita:",
        "pref.first_team":  "(prima squadra nel salvataggio)",
        "pref.default_form": "Formazione predefinita (Allenatore):",
        "pref.theme":       "Tema colori:",
        "pref.theme_retro": "Retro (blu Amiga / ambra / cyan)",
        "pref.theme_light": "Chiaro (alto contrasto accessibile)",
        "pref.system_font": "Usa font di sistema invece di Topaz retro",
        "pref.font_note":   "Font e tema si applicano al prossimo avvio.",
        "pref.skill_warn":  "Segnala giocatori con abilita' essenziali sotto 100 (\u26a0)",
        "pref.skill_warn_note": (
            "Avvisa es. un Port. con parata bassa, un Dif. con contrasto basso,"
            " un Att. con velocita' bassa.\n"
            "Si applica subito alla lista giocatori e alla scheda Stato."
        ),
        "pref.updates":     "Aggiornamenti",
        "pref.update_freq": "Controlli aggiornamenti automatici:",
        "pref.upd_disabled": "Disabilitato",
        "pref.upd_daily":   "Giornaliero",
        "pref.upd_weekly":  "Settimanale",
        "pref.upd_note": (
            'Un banner "Nuova versione disponibile" appare accanto al titolo\n'
            "quando viene trovata una versione piu' recente su GitHub."
            " Nessun dato inviato."
        ),
        "pref.language":  "Lingua",
        "pref.lang_note": "La lingua si applica al prossimo avvio.",
        "btn.cancel": "Annulla",
        "btn.save":   "Salva",
    },
}


def set_language(lang: str) -> None:
    """Set the active language. Call once at startup before building widgets."""
    global _lang
    if lang in _STRINGS:
        _lang = lang


def t(key: str) -> str:
    """Return the translated string for *key* in the active language.

    Falls back to English when the key is absent in the active language,
    and returns the key itself if not found in English either.
    """
    lang_table = _STRINGS.get(_lang, {})
    if key in lang_table:
        return lang_table[key]
    en_table = _STRINGS.get("en", {})
    return en_table.get(key, key)

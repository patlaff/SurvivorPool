import logging
from typing import NamedTuple

import pandas as pd

logger = logging.getLogger(__name__)

EventRow = tuple[str, int, str]  # (castaway_id, episode_number, event_name)

IDOL_TYPES = {'Hidden Immunity Idol', 'Immunity Idol', 'Hidden Immunity Idol (idol nullifier)'}
STANDARD_ADVANTAGE_TYPES = {
    'Hidden Immunity Idol', 'Immunity Idol',
    'Extra Vote', 'Steal-a-Vote', 'Steal a Vote',
    'Knowledge is Power', 'Amulet', 'Shot in the Dark',
    'Hidden Immunity Idol (idol nullifier)',
}


def _castaway_id_col(df: pd.DataFrame) -> str:
    for col in ('castaway_id', 'castaway'):
        if col in df.columns:
            return col
    return 'castaway'


# ── Idols & Advantages ────────────────────────────────────────────────────────

def detect_find_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    found = move[(move['event'] == 'Found') & (move['advantage_id'].isin(idol_ids))]
    col = _castaway_id_col(found)
    return [(row[col], int(row['episode']), 'find_idol') for _, row in found.iterrows()]


def detect_find_clue(tables: dict) -> list[EventRow]:
    details = tables['advantage_details']
    move = tables['advantage_movement']
    if details.empty or move.empty:
        return []
    clued = details[details['clue_details'].notna() & (details['clue_details'] != '')]['advantage_id'].unique()
    found = move[(move['event'] == 'Found') & (move['advantage_id'].isin(clued))]
    col = _castaway_id_col(found)
    seen: set = set()
    results = []
    for _, row in found.iterrows():
        key = (row[col], int(row['episode']))
        if key not in seen:
            seen.add(key)
            results.append((row[col], int(row['episode']), 'find_clue'))
    return results


def detect_gain_advantage(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    non_idol_ids = details[~details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    gained = move[
        (move['event'].isin(['Found', 'Received'])) &
        (move['advantage_id'].isin(non_idol_ids))
    ]
    col = _castaway_id_col(gained)
    return [(row[col], int(row['episode']), 'gain_advantage') for _, row in gained.iterrows()]


def detect_gain_2nd_advantage(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    non_idol_ids = details[~details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    gained = move[
        (move['event'].isin(['Found', 'Received'])) &
        (move['advantage_id'].isin(non_idol_ids))
    ]
    col = _castaway_id_col(gained)
    counts = gained.groupby([col, 'episode']).size()
    results = []
    for (castaway, ep), cnt in counts.items():
        if cnt >= 2:
            results.append((castaway, int(ep), 'gain_2nd_advantage'))
        if cnt >= 3:
            results.append((castaway, int(ep), 'gain_3rd_advantage'))
    return results


def detect_2nd_idol_in_week(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    found = move[
        (move['event'].isin(['Found', 'Received'])) &
        (move['advantage_id'].isin(idol_ids))
    ]
    col = _castaway_id_col(found)
    counts = found.groupby([col, 'episode']).size()
    return [
        (castaway, int(ep), '2nd_idol_in_week')
        for (castaway, ep), cnt in counts.items()
        if cnt >= 2
    ]


def detect_play_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    played = move[(move['event'] == 'Played') & (move['advantage_id'].isin(idol_ids))]
    col = _castaway_id_col(played)
    return [(row[col], int(row['episode']), 'play_idol') for _, row in played.iterrows()]


def detect_play_advantage(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    non_idol_ids = details[~details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    played = move[(move['event'] == 'Played') & (move['advantage_id'].isin(non_idol_ids))]
    col = _castaway_id_col(played)
    return [(row[col], int(row['episode']), 'play_advantage') for _, row in played.iterrows()]


def detect_saved_by_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    col = _castaway_id_col(move)
    results = []
    for _, row in move.iterrows():
        if (
            row['event'] == 'Played'
            and row['advantage_id'] in idol_ids
            and str(row.get('success', '')).upper() in ('TRUE', '1', 'YES')
            and 'played_for' in move.columns
            and pd.notna(row.get('played_for'))
        ):
            results.append((str(row['played_for']), int(row['episode']), 'saved_by_idol'))
    return results


def detect_vote_out_with_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    castaways = tables['castaways']
    if move.empty or details.empty or castaways.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    col = _castaway_id_col(move)
    c_col = _castaway_id_col(castaways)
    eliminated_eps: dict[str, int] = {}
    for _, row in castaways.iterrows():
        if str(row.get('result', '')).lower() in ('voted out', 'voted_out'):
            eliminated_eps[str(row[c_col])] = int(row.get('episode', 0))
    results = []
    for _, row in move.iterrows():
        if (
            row['event'] == 'Played'
            and row['advantage_id'] in idol_ids
            and str(row.get('success', '')).upper() in ('TRUE', '1', 'YES')
            and 'played_for' in move.columns
            and pd.notna(row.get('played_for'))
        ):
            target = str(row['played_for'])
            ep = int(row['episode'])
            if eliminated_eps.get(target) == ep:
                results.append((str(row[col]), ep, 'vote_out_with_idol'))
    return results


def detect_give_away_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    received = move[
        (move['event'] == 'Received') & (move['advantage_id'].isin(idol_ids))
    ].sort_values('sequence_id' if 'sequence_id' in move.columns else 'episode')
    results = []
    for _, row in received.iterrows():
        prev = move[
            (move['advantage_id'] == row['advantage_id']) &
            (move['event'] != 'Received')
        ]
        if 'sequence_id' in move.columns:
            prev = prev[prev['sequence_id'] < row['sequence_id']]
        if not prev.empty:
            giver_row = prev.iloc[-1]
            col = _castaway_id_col(giver_row.to_frame().T)
            results.append((str(giver_row[col]), int(row['episode']), 'give_away_idol'))
    return results


def detect_idol_received(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    idol_ids = details[details['advantage_type'].isin(IDOL_TYPES)]['advantage_id'].unique()
    received = move[(move['event'] == 'Received') & (move['advantage_id'].isin(idol_ids))]
    col = _castaway_id_col(received)
    return [(row[col], int(row['episode']), 'idol_received') for _, row in received.iterrows()]


def detect_lose_vote(tables: dict) -> list[EventRow]:
    votes = tables['vote_history']
    if votes.empty:
        return []
    col = _castaway_id_col(votes)
    lost = votes[votes['vote'].astype(str).str.lower().isin(['none', 'lost vote', 'no vote'])]
    return [(row[col], int(row['episode']), 'lose_vote') for _, row in lost.iterrows()]


def detect_steal_extra_vote(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    steal_ids = details[
        details['advantage_type'].str.lower().str.contains('extra vote|steal', na=False)
    ]['advantage_id'].unique()
    used = move[
        (move['event'].isin(['Played', 'Used'])) & (move['advantage_id'].isin(steal_ids))
    ]
    col = _castaway_id_col(used)
    return [(row[col], int(row['episode']), 'steal_extra_vote') for _, row in used.iterrows()]


# ── Approximated advantage events ─────────────────────────────────────────────

def detect_deny_advantage(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    if move.empty:
        return []
    nullified = move[move['event'].str.lower().str.contains('nullif', na=False)]
    col = _castaway_id_col(nullified)
    logger.debug('deny_advantage rows: %s', nullified[[col, 'episode', 'event']].to_dict('records'))
    return [(row[col], int(row['episode']), 'deny_advantage') for _, row in nullified.iterrows()]


def detect_disadvantage(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    disadv_ids = details[
        details['advantage_type'].str.lower().str.contains('disadvantage', na=False)
    ]['advantage_id'].unique()
    received = move[(move['event'] == 'Received') & (move['advantage_id'].isin(disadv_ids))]
    col = _castaway_id_col(received)
    logger.debug('disadvantage rows: %s', received[[col, 'episode']].to_dict('records'))
    return [(row[col], int(row['episode']), 'disadvantage') for _, row in received.iterrows()]


def detect_special_idol(tables: dict) -> list[EventRow]:
    move = tables['advantage_movement']
    details = tables['advantage_details']
    if move.empty or details.empty:
        return []
    special_ids = details[
        ~details['advantage_type'].isin(STANDARD_ADVANTAGE_TYPES)
        & details['advantage_type'].str.lower().str.contains('idol', na=False)
    ]['advantage_id'].unique()
    found = move[(move['event'] == 'Found') & (move['advantage_id'].isin(special_ids))]
    col = _castaway_id_col(found)
    logger.debug('special_idol types found: %s',
                 details[details['advantage_id'].isin(special_ids)]['advantage_type'].unique().tolist())
    return [(row[col], int(row['episode']), 'special_idol') for _, row in found.iterrows()]


def detect_exiled_from_tribe(tables: dict) -> list[EventRow]:
    # survivoR has a dedicated journeys table (Season 41+)
    journeys = tables.get('journeys', pd.DataFrame())
    if not journeys.empty and 'castaway_id' in journeys.columns and 'episode' in journeys.columns:
        col = _castaway_id_col(journeys)
        logger.debug('exiled_from_tribe journey rows: %d', len(journeys))
        return [(row[col], int(row['episode']), 'exiled_from_tribe') for _, row in journeys.iterrows()]
    # Fallback: look for journey/exile events in advantage_movement
    move = tables.get('advantage_movement', pd.DataFrame())
    if move.empty:
        return []
    exiled = move[move['event'].str.lower().str.contains('journey|exile', na=False)]
    col = _castaway_id_col(exiled)
    logger.debug('exiled_from_tribe rows: %s', exiled[[col, 'episode', 'event']].to_dict('records'))
    return [(row[col], int(row['episode']), 'exiled_from_tribe') for _, row in exiled.iterrows()]


def detect_medical_medevac(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    medevac = castaways[castaways['result'].str.lower().str.contains('medevac', na=False)]
    results = []
    for _, row in medevac.iterrows():
        ep = row.get('episode') or row.get('boot_episode')
        if pd.notna(ep):
            results.append((str(row[col]), int(ep), 'medical_medevac'))
    return results


# ── Challenges ────────────────────────────────────────────────────────────────

def detect_tribe_immunity(tables: dict) -> list[EventRow]:
    cr = tables['challenge_results']
    if cr.empty:
        return []
    col = _castaway_id_col(cr)
    # survivoR JSON provides explicit boolean columns — prefer them
    if 'won_tribal_immunity' in cr.columns:
        wins = cr[cr['won_tribal_immunity'] == True]  # noqa: E712
    else:
        wins = cr[
            cr.get('outcome_type', pd.Series()).str.lower().str.contains('tribal', na=False) &
            cr.get('challenge_type', pd.Series()).str.lower().str.contains('immunity', na=False) &
            (cr.get('result', pd.Series()).str.lower() == 'win')
        ]
    return [(row[col], int(row['episode']), 'tribe_immunity') for _, row in wins.iterrows()]


def detect_individual_immunity(tables: dict) -> list[EventRow]:
    cr = tables['challenge_results']
    if cr.empty:
        return []
    col = _castaway_id_col(cr)
    if 'won_individual_immunity' in cr.columns:
        wins = cr[cr['won_individual_immunity'] == True]  # noqa: E712
    else:
        wins = cr[
            cr.get('outcome_type', pd.Series()).str.lower().str.contains('individual', na=False) &
            cr.get('challenge_type', pd.Series()).str.lower().str.contains('immunity', na=False) &
            (cr.get('result', pd.Series()).str.lower() == 'win')
        ]
    return [(row[col], int(row['episode']), 'individual_immunity') for _, row in wins.iterrows()]


def detect_group_reward(tables: dict) -> list[EventRow]:
    cr = tables['challenge_results']
    if cr.empty:
        return []
    col = _castaway_id_col(cr)
    if 'won_tribal_reward' in cr.columns:
        wins = cr[cr['won_tribal_reward'] == True]  # noqa: E712
    elif 'won_team_reward' in cr.columns:
        wins = cr[cr['won_team_reward'] == True]  # noqa: E712
    else:
        wins = pd.DataFrame()
    return [(row[col], int(row['episode']), 'group_reward') for _, row in wins.iterrows()]


def detect_individual_reward(tables: dict) -> list[EventRow]:
    cr = tables['challenge_results']
    if cr.empty:
        return []
    col = _castaway_id_col(cr)
    if 'won_individual_reward' in cr.columns:
        wins = cr[cr['won_individual_reward'] == True]  # noqa: E712
    else:
        wins = pd.DataFrame()
    return [(row[col], int(row['episode']), 'individual_reward') for _, row in wins.iterrows()]


def detect_picked_for_reward(tables: dict) -> list[EventRow]:
    cr = tables['challenge_results']
    if cr.empty:
        return []
    col = _castaway_id_col(cr)
    # 'chosen_for_reward' is present in some versions of the data
    if 'chosen_for_reward' in cr.columns:
        picked = cr[cr['chosen_for_reward'] == True]  # noqa: E712
    else:
        picked = pd.DataFrame()
    return [(row[col], int(row['episode']), 'picked_for_reward') for _, row in picked.iterrows()]


# ── Tribal & Progression ──────────────────────────────────────────────────────

def detect_survive_tribal(tables: dict) -> list[EventRow]:
    votes = tables['vote_history']
    if votes.empty:
        return []
    col = _castaway_id_col(votes)
    attended = votes[votes['vote'].notna()].drop_duplicates(subset=[col, 'episode'])
    results = []
    for _, row in attended.iterrows():
        castaway = str(row[col])
        ep = int(row['episode'])
        # In survivoR JSON, voted_out_id is the castaway_id of who was eliminated.
        # voted_out is the display name (same value for all rows in a tribal).
        voted_out_id = row.get('voted_out_id')
        if pd.notna(voted_out_id) and castaway == str(voted_out_id):
            continue  # this person was voted out, not a survivor
        results.append((castaway, ep, 'survive_tribal'))
    return results


def detect_advance_a_week(tables: dict) -> list[EventRow]:
    boot = tables.get('boot_mapping', pd.DataFrame())
    if boot.empty:
        return []
    col = _castaway_id_col(boot)
    if 'status' in boot.columns:
        alive = boot[boot['status'].str.lower().str.contains('alive|active', na=False)]
    elif 'castaway_id' in boot.columns and 'episode' in boot.columns:
        # If no status column, treat all rows as "still in game" entries
        alive = boot
    else:
        return []
    return [(row[col], int(row['episode']), 'advance_a_week') for _, row in alive.iterrows()]


def detect_eliminated(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    elim = castaways[castaways['result'].str.lower().str.contains('voted out|voted_out', na=False)]
    results = []
    for _, row in elim.iterrows():
        ep = row.get('episode') or row.get('boot_episode')
        if pd.notna(ep):
            results.append((str(row[col]), int(ep), 'eliminated'))
    return results


def detect_quit_or_removed(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    quit_ = castaways[castaways['result'].str.lower().str.contains('quit|removed|disqualif', na=False)]
    results = []
    for _, row in quit_.iterrows():
        ep = row.get('episode') or row.get('boot_episode')
        if pd.notna(ep):
            results.append((str(row[col]), int(ep), 'quit_or_removed'))
    return results


def detect_make_jury(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    jury = castaways[castaways.get('jury', pd.Series(False)).astype(str).str.lower().isin(['true', '1', 'yes'])]
    results = []
    for _, row in jury.iterrows():
        ep = row.get('episode') or row.get('boot_episode')
        if pd.notna(ep):
            results.append((str(row[col]), int(ep), 'make_jury'))
    return results


def detect_finalist(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    finalists = castaways[
        castaways.get('finalist', pd.Series(False)).astype(str).str.lower().isin(['true', '1', 'yes']) &
        ~castaways.get('winner', pd.Series(False)).astype(str).str.lower().isin(['true', '1', 'yes'])
    ]
    results = []
    for _, row in finalists.iterrows():
        ep = castaways['episode'].max() if 'episode' in castaways.columns else 0
        results.append((str(row[col]), int(ep), 'finalist'))
    return results


def detect_sole_survivor(tables: dict) -> list[EventRow]:
    castaways = tables['castaways']
    if castaways.empty:
        return []
    col = _castaway_id_col(castaways)
    winners = castaways[castaways.get('winner', pd.Series(False)).astype(str).str.lower().isin(['true', '1', 'yes'])]
    results = []
    for _, row in winners.iterrows():
        ep = castaways['episode'].max() if 'episode' in castaways.columns else 0
        results.append((str(row[col]), int(ep), 'sole_survivor'))
    return results


def detect_win_fire_making(tables: dict) -> list[EventRow]:
    votes = tables['vote_history']
    if votes.empty:
        return []
    col = _castaway_id_col(votes)
    fire = votes[votes['vote'].astype(str).str.lower().str.contains('fire', na=False)]
    return [(row[col], int(row['episode']), 'win_fire_making') for _, row in fire.iterrows()]


def detect_survive_tiebreak(tables: dict) -> list[EventRow]:
    votes = tables['vote_history']
    if votes.empty:
        return []
    col = _castaway_id_col(votes)
    # survivoR JSON has an explicit 'tie' boolean column
    if 'tie' in votes.columns:
        tie_eps = votes[votes['tie'] == True]['episode'].unique()  # noqa: E712
    else:
        tie_eps = votes[votes['vote'].astype(str).str.lower().str.contains('tie|revote', na=False)]['episode'].unique()
    if len(tie_eps) == 0:
        return []
    tie_votes = votes[votes['episode'].isin(tie_eps)].drop_duplicates(subset=[col, 'episode'])
    results = []
    for _, row in tie_votes.iterrows():
        castaway = str(row[col])
        ep = int(row['episode'])
        voted_out_id = row.get('voted_out_id')
        if pd.notna(voted_out_id) and castaway == str(voted_out_id):
            continue
        results.append((castaway, ep, 'survive_tiebreak'))
    return results


def detect_go_to_rocks(tables: dict) -> list[EventRow]:
    votes = tables['vote_history']
    if votes.empty:
        return []
    col = _castaway_id_col(votes)
    rocks = votes[votes['vote'].astype(str).str.lower().str.contains('rock', na=False)]
    return [(row[col], int(row['episode']), 'go_to_rocks') for _, row in rocks.iterrows()]


def detect_reenter_game(tables: dict) -> list[EventRow]:
    boot = tables['boot_mapping']
    if boot.empty:
        return []
    col = _castaway_id_col(boot)
    if 'status' not in boot.columns:
        return []
    reenter = boot[boot['status'].str.lower().str.contains('return|reenter|re-enter', na=False)]
    return [(row[col], int(row['episode']), 'reenter_game') for _, row in reenter.iterrows()]


# ── Aggregator ────────────────────────────────────────────────────────────────

DETECTORS = [
    detect_find_idol, detect_find_clue, detect_gain_advantage,
    detect_gain_2nd_advantage, detect_2nd_idol_in_week,
    detect_play_idol, detect_play_advantage, detect_saved_by_idol,
    detect_vote_out_with_idol, detect_give_away_idol, detect_idol_received,
    detect_lose_vote, detect_steal_extra_vote,
    detect_deny_advantage, detect_disadvantage, detect_special_idol,
    detect_exiled_from_tribe, detect_medical_medevac,
    detect_tribe_immunity, detect_individual_immunity,
    detect_group_reward, detect_individual_reward, detect_picked_for_reward,
    detect_survive_tribal, detect_advance_a_week, detect_eliminated,
    detect_quit_or_removed, detect_make_jury, detect_finalist,
    detect_sole_survivor, detect_win_fire_making, detect_survive_tiebreak,
    detect_go_to_rocks, detect_reenter_game,
]


def detect_all_events(tables: dict, episode_number: int) -> list[EventRow]:
    all_events: list[EventRow] = []
    seen: set = set()

    for detector in DETECTORS:
        try:
            rows = detector(tables)
        except Exception:
            logger.exception('Error in detector %s', detector.__name__)
            continue

        for row in rows:
            castaway_id, ep, event_name = row
            if ep != episode_number:
                continue
            key = (castaway_id, ep, event_name)
            if key not in seen:
                seen.add(key)
                all_events.append(row)

    return all_events

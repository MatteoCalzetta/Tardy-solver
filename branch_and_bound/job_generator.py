import random
import math
from typing import List, Tuple, Optional

from job import Job

class JobGenerator:
    """
    Generatore con ID univoci globali.
    - self.next_id garantisce che ogni nuovo Job riceva un ID mai usato prima,
      anche se chiami generate() e generate_overloaded_blocks() più volte.
    - Puoi opzionalmente forzare un id di partenza con start_id (se >= next_id).
    """
    def __init__(self, seed: Optional[int] = None, start_id: int = 1):
        self.rnd = random.Random(seed)
        self.next_id = start_id

    # ---------- utilità ID ----------
    def _new_id(self) -> int:
        jid = self.next_id
        self.next_id += 1
        return jid

    def _maybe_set_start_id(self, start_id: Optional[int]):
        if start_id is not None and start_id >= self.next_id:
            self.next_id = start_id

    def reset_ids(self, start_id: int = 1):
        """Se proprio vuoi ripartire da un certo ID (di solito non serve)."""
        self.next_id = start_id

    # ---------- generatori ----------
    def generate(
        self,
        n_jobs: int,
        r_range: Tuple[int, int] = (0, 100),
        p_range: Tuple[int, int] = (1, 5),
        tightness: float = 0.2,
        mode: str = "tight",
        start_id: Optional[int] = None,
    ) -> List[Job]:
        """
        Generatore random standard (ritardi probabili ma NON garantiti).
        ID univoci anche tra chiamate diverse.

        - mode="tight": scadenze strette ⇒ più probabile avere job in ritardo.
        - mode="wide": scadenze larghe ⇒ pochi/nessun ritardo in media.
        - mode="mix": 70% tight, 30% wide.
        - tightness in [0, 1+] controlla lo slack: d = r + p + slack, con
          slack ∈ [0, round(tightness * p)] in modalità "tight".
        """
        self._maybe_set_start_id(start_id)

        jobs = []
        for _ in range(1, n_jobs + 1):
            r = self.rnd.randint(*r_range)
            p = self.rnd.randint(*p_range)

            pick_mode = mode
            if mode == "mix":
                pick_mode = "tight" if self.rnd.random() < 0.7 else "wide"

            if pick_mode == "wide":
                slack = self.rnd.randint(p, 3 * p)  # molto slack
            else:  # "tight"
                s_max = max(0, int(round(tightness * p)))
                slack = self.rnd.randint(0, s_max)

            d = r + p + slack
            jobs.append(Job(self._new_id(), r, p, d))
        return jobs

    def generate_overloaded_blocks(
        self,
        blocks: List[Tuple[int, int, float]],
        p_range: Tuple[int, int] = (1, 5),
        release_spread: float = 0.5,
        start_id: Optional[int] = None,
        extra_jobs: int = 0,
        outside_r_range: Tuple[int, int] = (0, 100),
        outside_slack_range: Tuple[int, int] = (5, 15),
    ) -> List[Job]:
        """
        Genera blocchi *sovraccarichi* che garantiscono ritardi.
        ID univoci anche tra chiamate diverse.

        blocks: lista di (start, length, overload) con overload > 1.0.
                In ogni blocco [start, start+length], si creano job con
                deadline = start+length finché la somma dei p >= overload * length.
        """
        self._maybe_set_start_id(start_id)

        jobs = []
        for start, length, overload in blocks:
            assert overload > 1.0, "overload deve essere > 1 per garantire ritardi"
            L = int(length)
            target_work = math.ceil(overload * L)
            total_p = 0

            max_release = start + max(0, int(release_spread * L))
            deadline = start + L

            while total_p < target_work:
                p = self.rnd.randint(*p_range)
                r = self.rnd.randint(start, max_release)
                jobs.append(Job(self._new_id(), r, p, deadline))
                total_p += p

        # Job extra “di contesto” con scadenze larghe
        for _ in range(extra_jobs):
            r = self.rnd.randint(*outside_r_range)
            p = self.rnd.randint(*p_range)
            slack = self.rnd.randint(*outside_slack_range)
            d = r + p + slack
            jobs.append(Job(self._new_id(), r, p, d))

        return jobs

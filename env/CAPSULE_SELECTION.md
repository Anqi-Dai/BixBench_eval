# How three capsules were chosen out of 54

The point of this diagram is not the shortlist. It is **which filters were free and
which had to be paid for**. Two of the five elimination criteria were discoverable
by reading metadata and inspecting the Docker image, at no cost. The other three
only became visible after spending money on a run — and one of them killed a
prediction rule that had looked sound.

```mermaid
flowchart TD
    START["<b>54 capsules</b><br/>BixBench v1.5 · 205 questions"]:::pool

    START --> SURVEY{{"<b>SURVEY</b><br/>metadata + image inspection<br/><i>$0</i>"}}:::survey

    SURVEY -->|"curator categories:<br/>no microbiome capsule exists"| CLUSTER["<b>RNA-seq / DE cluster</b><br/>22 capsules · 81 questions"]:::pool
    SURVEY -->|"questions need BWA, GATK,<br/>Trimmomatic — absent from image"| R61["bix-61<br/><i>unrunnable</i>"]:::rej

    CLUSTER --> PILOT{{"<b>PILOT at K=1</b><br/>one replica each<br/><i>$0.84 – $7.62</i>"}}:::pilot

    PILOT -->|"all 5 questions stopped at<br/>max_steps=20 · 2 gave no answer"| R43["bix-43, bix-53<br/><i>truncated</i>"]:::rej
    PILOT -->|"$7.62/replica — 5.6× bix-8<br/>despite the shortest questions"| R4["bix-4<br/><i>too expensive</i>"]:::rej
    PILOT -->|"$1.35 · 9–14 actions<br/>never near the ceiling"| S8["<b>bix-8</b><br/>6 questions"]:::sel
    PILOT -->|"$2.36 · independent family"| S26["<b>bix-26</b><br/>3 questions"]:::sel
    PILOT -->|"$0.84 — cheapest,<br/>but only 2 questions"| B1["bix-1"]:::mid

    B1 --> FAM["<b>within-family test</b><br/>bix-1 vs bix-49 differ by <b>3%</b><br/>bix-1 vs bix-26, same topic, by <b>87%</b>"]:::find
    FAM -->|"family predicts cost;<br/>topic and question length do not"| S49["<b>bix-49</b><br/>5 questions"]:::sel
    FAM -.->|"superseded — same family,<br/>fewer questions"| DROP1["bix-1<br/><i>dropped</i>"]:::rej

    S8 -.->|"shares a source paper with bix-8;<br/>3 capsules cannot identify<br/>a paper-level variance"| R37["bix-37<br/><i>not independent</i>"]:::rej

    S8 --> FINAL["<b>K=10 campaign</b><br/>14 questions · 140 trajectories"]:::final
    S49 --> FINAL
    S26 --> FINAL

    classDef pool fill:#e8eef7,stroke:#4a6fa5,stroke-width:2px,color:#1a2b45
    classDef survey fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#12305e
    classDef pilot fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#5c3a00
    classDef sel fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#0f3d20
    classDef rej fill:#fee2e2,stroke:#dc2626,stroke-width:1.5px,color:#5c1010
    classDef mid fill:#f3f4f6,stroke:#6b7280,stroke-width:1.5px,color:#1f2937
    classDef find fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#3b1f7a
    classDef final fill:#16a34a,stroke:#14532d,stroke-width:3px,color:#ffffff
```

**Colors carry meaning:** blue is a free survey step, amber is a step that cost
money, purple is the measurement that produced a usable rule, green is selected,
red is eliminated, and each arrow says *why*.

## What the diagram is arguing

**Only two eliminations were free.** The absent microbiome capsules came from the
curators' own `categories` field, and bix-61's missing toolchain came from listing
what the Docker image actually contains. Everything below the amber box required
running the agent.

**The expensive filters could not have been predicted.** bix-4 had the *shortest*
questions of any candidate and was forecast to be the cheapest; it cost 5.6× bix-8.
Truncation on bix-43 and bix-53 was likewise invisible until the runs stopped dead
at exactly 20 actions.

**One rule did survive.** bix-1 and bix-49 come from the same source paper and
differ by 3% per rollout; bix-1 and bix-26 share a topic but different papers and
differ by 87%. So one pilot per *family* generalizes to its siblings, while topic
and question length do not. That is the only reusable planning tool the exercise
produced, and it cost about $20 to find.

**bix-37 was rejected for a statistical reason, not an empirical one.** It shares a
source paper with bix-8, and with three capsules there is no way to identify a
paper-level variance component — the dependence would have to be assumed away
rather than modelled.

## Regenerating

The diagram is Mermaid source in this file; GitHub renders it directly. To export
an image, paste the fenced block into <https://mermaid.live>. The underlying
numbers come from `results/capsule_pilot_log.csv`, regenerated with
`python py/pilot_table.py`.

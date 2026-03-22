# PFI Graph Test — Build Agent Brief

## What This Is

You are building a test. Not a product. Not a platform. A test that answers one question:

**Does permitting data, when organized as a living graph rather than a static database, express meaningful structure around regulatory escalation before that escalation happens?**

If yes, a larger system gets built. If no, the approach gets abandoned and the project continues as a conventional database product.

Everything in this document is in service of answering that one question.

---

## The Purpose Of The System

Before anything else understand this because it determines every decision you make about what to build and what to ignore.

Every PE infrastructure fund, asset manager, and developer is focused on their own project. Their lawyers track their specific permit. Their consultants know their specific jurisdiction. Their internal models reflect their specific experience. They are on the web building their section of it. They cannot see the whole web from where they are standing.

The purpose of this system is to give those funds visibility on the market that they structurally cannot have by only looking inward.

Specifically the system exists to answer the questions these funds actually care about at a first principles level:

- Is the permitting variance my project is experiencing normal for this project type in this jurisdiction or is it an outlier
- Is the regulatory resistance forming around my project an isolated local event or part of a broader pattern moving across jurisdictions
- Are the conditions that preceded full blockage in comparable projects present in my jurisdiction right now
- Which permitting path has historically moved faster for a project like mine in a market like this

These are not data questions. They are capital allocation questions. A fund with $500M deployed into a project that is stalling needs to know whether to fight, reroute, or reprice. Right now they answer that question with internal judgment and consultant opinion.

This system answers it with the shape of everything that has ever happened to every comparable project across every comparable jurisdiction simultaneously.

That is what the graph is for. Not academic pattern recognition. Not a research product. Giving funds a view of the market they cannot build internally because they are inside it.

---

## Background Context

### What PFI Is

PFI (Permitting Friction Index) is an empirical index built entirely from public records. It measures elapsed time between permitting milestones across large scale infrastructure projects in Texas, Georgia, and Arizona going back to 2018.

It records what happened. When it happened. How long it took. Across comparable projects.

It does not predict. It does not rank. It does not recommend.

The data is real. The corpus exists. The collection system works.

### The Problem With The Current Approach

Right now PFI is a database that gets queried. A user asks a question. The system returns a historical record. That is useful but it is not differentiated. A well resourced competitor with the same data can produce the same output.

### The Hypothesis Being Tested

The hypothesis is this:

If you stop treating permitting data as rows to be queried and start treating it as a living structure where every new entry changes the shape of everything already in the system, something becomes visible that was never visible before.

Specifically: the system should be able to express the position of an early stage regulatory action relative to every comparable action that preceded escalation in the historical record. Without being told what to look for. Without a human defining the categories. Without a query being run.

The structure itself should express whether an early permitting action looks like the beginning of a pattern that historically escalated into blockage.

This is the concept of emergence applied to permitting data. The pattern was always in the data. The question is whether organizing the data as a dynamic graph makes it visible before any individual project can see it coming.

---

## The Test

### What You Are Testing

You are not testing a product. You are testing whether the force is real.

You have four cases where the full sequence of events is known and documented in public records:

1. **Van Zandt County, Texas** — Battery Energy Storage System (BESS) blockage
2. **Gillespie County, Texas** — BESS blockage
3. **Katy (City), Texas** — BESS zoning denial (Vesper Energy / Ochoa BESS)
4. **Newton County, Georgia** — Data center moratorium

Each of these cases has a complete public record. Resolution or early action. Escalation. Final blockage. The full sequence is known.

### How The Test Works

**Step one:** Feed the complete historical corpus into the graph. Every permitting action across every project in the dataset. Every jurisdiction. Every project type. Every agency. All of it. This is the baseline structure.

**Step two:** For each of the four test cases, remove everything that happened after the first regulatory action. For Van Zandt that means removing everything after the county moratorium was first passed. Feed the system only what was publicly known at that earliest moment.

**Step three:** Without asking the system a specific question, read what the graph expresses. Where does that early action sit relative to the full corpus. What does it connect to. What does its position in the structure look like.

**Step four:** Compare what the graph expressed to what actually happened. Did the position of that early action in the graph resemble the position every other early action occupied before it escalated into full blockage.

If yes across three or four cases the approach works.
If no the approach does not work in this domain and you know before building the larger system.

---

## The Four Test Cases — What You Need To Know

### Case 1: Van Zandt County, Texas

**Project:** Amador Energy Storage Project — 220 MW battery energy storage system (BESS), 48 acres, Van Zandt County, TX. Owned by Taaleri Energia North America LLC.

**The sequence:**
- December 2024: 20 county residents filed a damages and injunction lawsuit (Cause No. 24-00204)
- April 9, 2025: Temporary Restraining Order issued by 294th Judicial District Court (Cause No. 25-00067)
- February 11, 2026: Van Zandt County Commissioners unanimously passed a county-wide moratorium halting all 17 green energy projects using state fire codes and a Section 391 commission

**Legal mechanism used:** Fire code enforcement (NFPA standards) plus Section 391 commission. Not zoning.

**For the test:** Feed only the December 2024 resident lawsuit. Remove everything after. See what the graph expresses.

---

### Case 2: Gillespie County, Texas

**Project:** Rogers Draw BESS — 145 MW battery energy storage system, Harper, Gillespie County, TX. $317M project. Developer: Peregrine Energy Solutions.

**The sequence:**
- February 2025: Gillespie County Commissioners passed a resolution opposing all BESS projects
- Following months: Gillespie County filed a lawsuit against the project citing health, safety, and environmental concerns
- December 2025: County issued formal Stop Work Orders to Peregrine Energy and Rogers Draw Energy
- Active: Judge Albert Patillo of the 216th District Court issued a court order halting all construction until final judgment

**Legal mechanism used:** Health and safety litigation through district court. Not zoning. Not fire code.

**For the test:** Feed only the February 2025 commissioner resolution. Remove everything after. See what the graph expresses.

---

### Case 3: Katy, Texas (Vesper Energy / Ochoa BESS)

**Project:** Ochoa Energy Storage — 500 MW standalone BESS, 24-acre site inside Katy city limits, Harris County, TX. Developer: Vesper Energy. Backer: GCM Grosvenor.

**The sequence:**
- Katy City Council denied the Special Use Permit after months of homeowner opposition
- Vesper Energy appealed to the Public Utility Commission of Texas (PUCT) arguing the city had no authority to block a grid-connected battery facility
- ERCOT intervened stating the city's denial directly affects grid authority
- PUCT agreed to review. Hearing scheduled 2026. No ruling yet.

**Why this case is different:** This is the first major test of whether Texas cities can use local zoning to block ERCOT-jurisdictional energy storage. The outcome could set statewide precedent. A ruling in Vesper's favor would invalidate municipal zoning denials of grid-connected BESS projects specifically. It would not affect county fire code enforcement or district court health and safety injunctions.

**Legal mechanism used:** Municipal zoning denial. Different from Cases 1 and 2.

**For the test:** Feed only the initial Special Use Permit denial. Remove everything after. See what the graph expresses and specifically whether it distinguishes this mechanism from the mechanisms in Cases 1 and 2.

---

### Case 4: Newton County, Georgia

**Project:** Data center development — multiple proposals in Newton County, GA including Meta's existing campus and various new proposals along the I-20 corridor.

**The sequence:**
- Wave of community opposition building through 2025
- Newton County enacted an emergency moratorium on data center development
- County extended the moratorium
- Social Circle (adjacent jurisdiction) enacted a 90-day moratorium on new data center submissions
- Georgia legislature introduced HB 1012 proposing a statewide one-year construction moratorium

**Why this case matters:** Shows the pattern jumping from county level to adjacent jurisdictions to state level legislation. The escalation path is different from the Texas BESS cases.

**Legal mechanism used:** Emergency moratorium through commissioner authority. Then legislative escalation.

**For the test:** Feed only the initial community opposition actions before the moratorium. See what the graph expresses about trajectory.

---

## Technical Architecture For The Test

### What To Build

A graph database populated with the full PFI corpus, structured so that:

- Every permitting action is a node
- Every relationship between actions is a weighted edge
- Weights are determined by similarity across four dimensions: jurisdiction type, project type, legal mechanism used, and sequence position

### Recommended Stack

**Graph database:** Neo4j. It stores nodes and relationships natively. It is the most established tool for this type of structure. It has a free community edition sufficient for this test.

**Embedding model:** Use a pretrained model to convert each permitting action into a vector representation. This allows the graph to measure similarity between actions mathematically rather than through human defined categories. Sentence transformers work for this. The model does not need to be custom trained for this test.

**Similarity calculation:** When a new node enters the graph, calculate its cosine similarity to every existing node across the four dimensions above. Create weighted edges to the most similar nodes. The weight reflects how similar this action is to that historical action.

**Visualization:** Use Neo4j Bloom or a simple D3.js rendering to visualize the graph structure at each stage of the test. You need to be able to see visually where a new node sits in the structure relative to the full corpus.

### What You Are NOT Building

- A user interface
- A query system
- A reporting layer
- A prediction engine
- A recommendation system

You are building the minimum structure needed to see whether the graph expresses meaningful position for an early stage regulatory action relative to the full corpus.

Nothing more.

---

## The Four Dimensions For Edge Weighting

These are the only four human defined inputs into the system. Everything else emerges from the data.

**1. Jurisdiction type**
- Municipal (city council, mayor)
- County commissioner
- State agency (TCEQ, PUCT, ERCOT)
- Federal agency (DOI, FERC, BLM, USFWS)
- District court
- Appellate court

**2. Project type**
- Battery Energy Storage System (BESS)
- Utility scale solar
- Wind
- Natural gas generation
- Data center
- LNG export terminal
- Semiconductor fabrication
- Combined (solar plus storage, gas plus data center, etc.)

**3. Legal mechanism**
- Zoning denial
- Fire code enforcement
- Health and safety litigation
- Commissioner resolution
- Emergency moratorium
- Permit denial by agency
- Court injunction or stop work order
- Legislative action (bill, statute)
- Federal review escalation (elevated review, vacatur)

**4. Sequence position**
- First public action in jurisdiction against project type
- Escalation from prior action in same jurisdiction
- Escalation from prior action in adjacent jurisdiction
- Legislative response to local pattern
- Court response to agency action

---

## What Success Looks Like

The test succeeds if the graph, when fed only the earliest action in each test case, places that action in a position that is structurally similar to the position every other first action occupied before full escalation occurred.

You do not need the graph to tell you what will happen. You need the graph to show that the early action looks structurally like other early actions that escalated. That is enough to validate the approach.

The test fails if the early action sits in a position that is structurally indistinguishable from actions that did not escalate. That means the signal is not in the data at the scale you currently have or the graph structure is not the right lens.

---

## What Failure Means

Failure does not mean the project is dead. It means the emergence hypothesis does not hold at current corpus scale or with current graph structure.

If the test fails you still have a valid database product with a real methodology and a real dataset. You rebuild around that and revisit the graph approach when the corpus is larger.

---

## What To Deliver

1. Neo4j graph populated with the full PFI corpus structured across the four dimensions above
2. Four test runs, one per case, with visualizations showing where the early action sits in the graph structure
3. A simple written record of what the graph expressed in each case versus what actually happened
4. A clear yes or no on whether the structure expressed meaningful position before escalation occurred

That is the entire scope of this build.

---

## One Rule

Do not tell the system what to find. Define the force. Feed the data. Read what emerges.

The force is: find the true shape of how regulatory resistance moves through infrastructure development so that a fund looking at their own project can see where they sit relative to everything that has ever happened to every comparable project before them.

The output is not a pattern for its own sake. It is the market view that no single fund can build from inside their own portfolio. The spider cannot see the whole web. This system is the view from outside it.

Everything else the system figures out on its own or it doesn't. That is the test.

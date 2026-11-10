"""The home page: the claim, the cohort, the invitation, the results and how they were produced."""
from collections import Counter

from .core import WORDS, axis_th, esc, fail, key, plot_td, slug
from .source import has
from .studies import AX3, all_studies, table, th

NUMWORD = {v: k for k, v in WORDS.items()}


def mailto(S, subject):
    return f'mailto:{esc(S["email"])}?subject={subject.replace(" ", "%20")}'


def hero(S):
    fig = S["fig"]["IP assignment"]
    a, b = fig["Assertion only"], fig["Adversarial bundle"]
    body = []
    for name in a:
        x, y = a[name][1], b[name][1]
        body.append(f'<tr data-model="{slug(name)}"><th scope="row">{esc(name)}</th>' + plot_td(*AX3, [
            dict(v=x["v"], lo=x["lo"], hi=x["hi"], on=x["star"], track="a"),
            dict(v=y["v"], lo=y["lo"], hi=y["hi"], on=y["star"], track="b", shape="d")]) + "</tr>")
    head = "<tr>" + th("Model") + axis_th("Change in P, points", *AX3) + "</tr>"
    figure = (
        '<figure class="herofig"><figcaption><strong><a href="#ip-assignment">IP assignment, no deed ever signed</a></strong>'
        "<span>How far each model moved toward the party asserting the assignment</span></figcaption>"
        + table("IP assignment, no executed deed, soft anchor: change in P against the honest record",
                head, body, ' class="fig"')
        + key(("mk", "the party asserts the assignment"), ("mk d", "the party curates and misstates the record"),
              ("mk on", "filled: Holm p < 0.05")) + "</figure>")
    n = NUMWORD[S["n_studies"]].capitalize()
    return f"""<div class="wrap hero">
<div>
<p class="eyebrow">Working paper, {esc(S["date"])}</p>
<h1>Can the other side steer your AI lawyer?</h1>
<p class="lede">{n} experiments on {S["n_models"]} models. Telling the reviewer what to conclude rarely worked. Controlling what the record showed did.</p>
<div class="cta"><a class="btn primary" href="paper/">Read the paper</a><a href="data/">Data and code</a></div>
</div>
{figure}
</div>"""


def cohort(S):
    has(S, "each against the same model's clean control")
    c, d, i, r = S["scen"]
    routes = Counter(m["route"] for m in S["models"])
    by_route = ", ".join(f"{n} by {route}" for route, n in routes.most_common()).replace("Direct API", "direct API")
    stats = (
        (S["n_studies"], "studies", "Contract review, interpretive drift, IP assignment, due diligence"),
        (S["n_models"], "models", by_route),
        ("About " + S["n_assess"], "assessments", "Each scored against the same model's clean control"),
        (sum(S["scen"]), "fictional scenarios",
         f"{c} contract issue set, {d} drift cases, {i} IP cases, {r} data rooms"))
    cells = "".join(f'<div class="stat"><b>{esc(a)}</b><span>{b}</span><small>{esc(s)}</small></div>'
                    for a, b, s in stats)
    return (f'<div class="wrap"><div class="stats">{cells}</div>'
            '<div class="invite"><p>This is a working paper and has not been peer reviewed. '
            "Corrections and criticism are welcome, and every correction so far is listed on this site.</p>"
            f'<a href="{mailto(S, "Feedback on the working paper")}">Send feedback</a></div></div>')


def results(S):
    jumps = (("contract-review", "Contract review"), ("interpretive-drift", "Interpretive drift"),
             ("ip-assignment", "IP assignment"), ("due-diligence", "Due-diligence pipeline"))
    jump = "".join(f'<a href="#{a}">{b}</a>' for a, b in jumps)
    opts = '<option value="">None</option>' + "".join(
        f'<option value="{m["slug"]}">{esc(m["name"])}</option>' for m in S["models"])
    return f"""<section class="sec" id="results"><div class="wrap">
<h2>Results</h2>
<p class="lead">{esc(S["closing"])}</p>
<div class="bar"><nav class="jump" aria-label="Studies">{jump}</nav>
<label class="ctl needs-js">Highlight model <select id="hl">{opts}</select></label></div>
{all_studies(S)}
</div></section>"""


def approach(S):
    has(S, "All fixtures are fictional", "an AI assistant drafted the documents",
        "no client or confidential information was used", "20 replicates",
        "95\\% bootstrap confidence intervals", "(10,000 permutations)",
        "with 100,000 permutations changed no mark",
        "GPT-6.1 Sol coded every contract review and DD output without seeing the condition",
        "independently coded a deterministic random 10\\% sample",
        "issue position $\\kappa = 0.74$", "naming the manipulation $\\kappa = 0.81$",
        "blinded, label-stratified sample of 200 items", "$\\kappa = 0.54$ on issue position and $0.91$ on framing adoption",
        "The judge therefore overstates absolute skew",
        "once with Claude and once with GPT-6 Astra",
        "specified each scenario and the conditions to test", "as a research and drafting assistant",
        "prepared the fixture documents, the test harness and the analysis code",
        "produced drafts of the text and figure",
        "no model provider or legal-technology vendor sponsored or endorsed it")
    fixes = [b for b in S["validation"] if b[0] == "table"]
    if not fixes:
        fail("no corrections table in the validation log")
    n_fix = len(fixes[0][2])
    reps = Counter(m["reps"] for m in S["models"])
    by_reps = ", ".join(f"{n} model{'' if n == 1 else 's'} at {r} replicates" for r, n in sorted(reps.items(), reverse=True))
    mrows = "".join(
        f'<tr data-model="{m["slug"]}"><th scope="row">{esc(m["name"])}</th><td class="t">{esc(m["group"])}</td>'
        f'<td class="t">{esc(m["route"])}</td><td class="n">{m["reps"]}</td></tr>' for m in S["models"])
    mtable = table("Models, access routes and replicates per cell",
                   "<tr>" + th("Model") + th("Group") + th("Route") + th("Replicates per cell", num=True) + "</tr>",
                   [mrows])
    rows = (
        ("Fictional case files",
         "<p>Every scenario is fictional. A lawyer specified each one and an AI assistant drafted the documents. "
         "No client or confidential information was used.</p>"),
        ("Each model against itself",
         "<p>Every effect is a model's result under a manipulation minus the same model's result on the clean "
         "record, in the same task and setting.</p>"),
        (f"{S['n_models']} models, {len(set(m['route'] for m in S['models']))} access routes",
         f"<p>{by_reps[0].upper() + by_reps[1:]}.</p><details><summary>All models and access routes</summary>{mtable}</details>"),
        ("Statistics",
         "<p>Means with 95% bootstrap confidence intervals. Permutation tests against the control with 10,000 "
         "permutations, Holm-corrected across the conditions within each model and setting. Rechecking the "
         "borderline results with 100,000 permutations changed no mark.</p>"),
        ("Coding",
         "<p>GPT-6.1 Sol coded every contract review and due-diligence output without seeing the condition. "
         "Opus 5.5 independently coded a 10% sample: kappa 0.74 on issue position and 0.81 on naming the "
         "manipulation.</p><p>The author then coded 200 items blind: kappa 0.54 on issue position and 0.91 on "
         "framing adoption. The automated judge overstates absolute skew, so the contract-review effects are, "
         "if anything, smaller than reported.</p>"),
        ("Recomputed twice",
         "<p>The reported results were recomputed from the raw records twice, independently: once with Claude "
         f'and once with GPT-6 Astra. The two passes led to {n_fix} corrections, <a href="corrections/">each '
         "one listed</a>.</p>"),
        ("AI assistance and funding",
         "<p>The author set the question, specified the scenarios, directed the work and did the blind "
         "human coding. Claude, used as a research and drafting assistant, prepared the fixtures and the "
         "code to the author's specifications, ran the experiments and produced drafts of the paper. No "
         "model provider or legal-technology vendor sponsored or endorsed the work.</p>"))
    dl = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in rows)
    return (f'<section class="sec" id="approach"><div class="wrap"><h2>Approach</h2>'
            f'<dl class="rows">{dl}</dl></div></section>')


def questions(S):
    limits = "".join(f"<div><dt>{esc(t)}</dt><dd><p>{esc(x)}</p></dd></div>" for t, x in S["limits"])
    future = "".join(f"<li>{esc(x)}</li>" for x in S["future"])
    return f"""<section class="sec" id="open-questions"><div class="wrap">
<h2>Limits and open questions</h2>
<h3>What this does not show</h3>
<dl class="rows">{limits}</dl>
<h3>What should be tested next</h3>
<ul class="list">{future}</ul>
<div class="close"><p>Found an error, a rival explanation or a case that breaks the pattern? Write to the author. Corrections are logged with the date and what changed.</p>
<a class="btn primary" href="{mailto(S, "Feedback on the working paper")}">Send feedback</a></div>
</div></section>"""


def home(S):
    return hero(S) + cohort(S) + results(S) + approach(S) + questions(S)

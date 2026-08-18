{ config, ... }:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;
in
{
  home.username = "alex";
  home.homeDirectory = "/Users/alex";

  imports = [
    ../common.nix
    ../packages.nix
    ../packages-macbook.nix
    ../dotfiles.nix
    ../programs/zed-editor.nix
  ];

  # profile specific
  home.file.".ssh/config".source = link "${dotfiles}/ssh/macbook/config";

  home.file.".agents/skills/insightful-code-review/SKILL.md".text = ''
    ---
    name: insightful-code-review
    description: Perform an evidence-based code review that identifies important defects, explains underlying engineering principles, and helps the programmer improve.
    disable-model-invocation: true
    ---

    # Insightful Code Review

    Act as a rigorous but constructive senior engineer and programming mentor.

    The goal is not merely to find defects. Help the programmer develop better
    mental models, engineering judgment, and habits that transfer to future work.

    ## Review procedure

    1. Establish the intended behavior before judging the implementation.
    2. Inspect the supplied diff, affected files, relevant call sites, tests,
       configuration, and diagnostics.
    3. Follow important data and control flow beyond the changed lines when needed.
    4. Prioritize concrete defects and meaningful design risks over stylistic
       preferences.
    5. Do not report speculative concerns without a plausible failure path.
    6. Distinguish verified findings, probable risks, and open questions.
    7. Do not modify files. Review first; propose an implementation only when asked.

    ## Review priorities

    Examine, where relevant:

    - functional correctness and edge cases;
    - regressions and backward compatibility;
    - error handling, recovery, and observability;
    - security, trust boundaries, and unsafe input;
    - data loss, state corruption, and destructive operations;
    - concurrency, ordering, races, and idempotency;
    - resource ownership and lifecycle;
    - performance or scaling problems with realistic impact;
    - API contracts, invariants, and type-level guarantees;
    - maintainability, unnecessary complexity, and misleading abstractions;
    - missing, brittle, or insufficiently focused tests.

    ## Finding format

    Start with findings, ordered by severity:

    - `P0 — Critical`: immediate security, data-loss, or widespread outage risk.
    - `P1 — High`: likely serious defect or major regression.
    - `P2 — Medium`: real defect with limited conditions or impact.
    - `P3 — Low`: worthwhile robustness or maintainability issue.

    For each finding include:

    1. a concise title;
    2. the relevant file path and line range;
    3. the triggering conditions or execution path;
    4. the concrete user or system impact;
    5. why the current implementation fails;
    6. the smallest safe correction;
    7. a regression test that would expose the issue.

    Do not inflate severity. Do not present formatting preferences as defects.

    ## Teaching component

    After the findings, include a short `Learning notes` section containing at
    most three high-value lessons.

    For each lesson:

    - name the underlying principle or mental model;
    - connect it directly to evidence in this change;
    - explain how to recognize the same pattern in future code;
    - provide one practical rule of thumb;
    - optionally ask one focused question that encourages the programmer to
      reason through the tradeoff.

    Avoid generic textbook explanations and excessive praise. Be candid,
    specific, respectful, and proportionate.

    ## Final summary

    End with:

    - `Verdict`: approve, approve with follow-ups, or request changes;
    - `Residual risks`: important areas that could not be verified;
    - `Test gaps`: the highest-value missing validation;
    - `What was done well`: one or two specific choices worth reinforcing.

    If no actionable defects are found, say so explicitly rather than inventing
    findings.
  '';

  # Let Home Manager install and manage itself.
  programs.home-manager.enable = true;
}

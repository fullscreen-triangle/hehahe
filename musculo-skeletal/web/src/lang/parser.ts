/**
 * Recursive-descent parser. The grammar is LL(1), so one token of
 * lookahead suffices and no backtracking is used.
 *
 * Both `outbound` and `return` are mandatory in a circuit declaration, so
 * an open circuit cannot arise by omission -- only through an explicit
 * `without` / `reroute` operator inside an experiment.
 */

import {
  type AntagonistDecl, type CircuitDecl, type CircuitExpr,
  type ElementDecl, type EventTypeDecl, type ExperimentDecl,
  type FloorSpec, type InstanceDecl, type LesionDecl, type Observable,
  type PhaseDecl, type Program, type Quantity, type Span,
  type TemplateDecl, emptyProgram,
} from "./ast";
import { STRATA, type Stratum, type Token, tokenize } from "./lexer";

export class ParseError extends Error {
  constructor(msg: string, public token: Token) {
    super(`${msg} (got '${token.text || "<eof>"}' at line ${token.line}, col ${token.col})`);
  }
}

class Parser {
  private i = 0;
  private toks: Token[];

  constructor(toks: Token[]) {
    // Comments never reach the parser.
    this.toks = toks.filter((t) => t.kind !== "comment");
  }

  private get cur(): Token {
    return this.toks[this.i];
  }

  private span(t: Token = this.cur): Span {
    return { line: t.line, col: t.col, start: t.start, end: t.end };
  }

  private at(kind: Token["kind"], text?: string): boolean {
    const t = this.cur;
    return t.kind === kind && (text === undefined || t.text === text);
  }

  private atKw(...words: string[]): boolean {
    return this.cur.kind === "keyword" && words.includes(this.cur.text);
  }

  private eat(kind: Token["kind"], text?: string): Token {
    if (!this.at(kind, text)) {
      throw new ParseError(`expected ${text ?? kind}`, this.cur);
    }
    return this.toks[this.i++];
  }

  private kw(word: string) {
    return this.eat("keyword", word);
  }
  private punct(ch: string) {
    return this.eat("punct", ch);
  }

  /** Stratum names are keywords but legal in identifier position. */
  private ident(): string {
    if (this.cur.kind === "keyword" && (STRATA as readonly string[]).includes(this.cur.text)) {
      return this.toks[this.i++].text;
    }
    return this.eat("ident").text;
  }

  private quantity(): Quantity {
    const t = this.cur;
    if (t.kind === "quantity") {
      this.i++;
      return { value: t.value!, unit: t.unit! };
    }
    if (t.kind === "number") {
      this.i++;
      return { value: t.value!, unit: "" };
    }
    throw new ParseError("expected a quantity", t);
  }

  private number(): number {
    const t = this.cur;
    if (t.kind === "number" || t.kind === "quantity") {
      this.i++;
      return t.value!;
    }
    throw new ParseError("expected a number", t);
  }

  // ── program ───────────────────────────────────────────────────────

  parseProgram(): Program {
    const prog = emptyProgram();

    if (this.atKw("module")) {
      this.kw("module");
      prog.module = this.ident();
      this.punct(";");
    }
    while (this.atKw("import")) {
      this.kw("import");
      prog.imports.push(this.ident());
      this.punct(";");
    }

    while (!this.at("eof")) {
      if (this.atKw("compartment")) {
        prog.compartments.push(this.parseCompartment());
      } else if (this.atKw("circuit")) {
        const d = this.parseCircuitLike();
        if (d.kind === "template") prog.templates.push(d);
        else if (d.kind === "instance") prog.instances.push(d);
        else prog.circuits.push(d);
      } else if (this.atKw("event")) {
        prog.eventTypes.push(this.parseEventType());
      } else if (this.atKw("antagonist")) {
        prog.antagonists.push(this.parseAntagonist());
      } else if (this.atKw("experiment")) {
        prog.experiments.push(this.parseExperiment());
      } else {
        throw new ParseError("expected a declaration", this.cur);
      }
    }
    return prog;
  }

  private parseCompartment() {
    const t0 = this.kw("compartment");
    const name = this.ident();
    this.punct("{");
    this.kw("capacitance");
    this.punct(":");
    const capacitance = this.quantity();
    this.punct(";");
    this.kw("stratum");
    this.punct(":");
    if (!this.atKw(...STRATA)) throw new ParseError("expected a stratum name", this.cur);
    const stratum = this.toks[this.i++].text as Stratum;
    this.punct(";");
    this.punct("}");
    return { kind: "compartment" as const, name, capacitance, stratum, span: this.span(t0) };
  }

  private parseCircuitLike(): CircuitDecl | TemplateDecl | InstanceDecl {
    const t0 = this.kw("circuit");

    if (this.atKw("template")) {
      this.kw("template");
      const name = this.ident();
      this.punct("(");
      const params: string[] = [];
      if (!this.at("punct", ")")) {
        params.push(this.ident());
        while (this.at("punct", ",")) {
          this.punct(",");
          params.push(this.ident());
        }
      }
      this.punct(")");
      const body = this.parseCircuitBody();
      return { kind: "template", name, params, ...body, span: this.span(t0) };
    }

    const name = this.ident();

    if (this.at("punct", "=")) {
      this.punct("=");
      const template = this.ident();
      this.punct("(");
      const args: (string | Quantity)[] = [];
      if (!this.at("punct", ")")) {
        args.push(this.templateArg());
        while (this.at("punct", ",")) {
          this.punct(",");
          args.push(this.templateArg());
        }
      }
      this.punct(")");
      this.punct(";");
      return { kind: "instance", name, template, args, span: this.span(t0) };
    }

    const body = this.parseCircuitBody();
    return { kind: "circuit", name, ...body, span: this.span(t0) };
  }

  private templateArg(): string | Quantity {
    if (this.cur.kind === "number" || this.cur.kind === "quantity") return this.quantity();
    return this.ident();
  }

  private parseCircuitBody() {
    this.punct("{");
    this.kw("floor");
    this.punct(":");
    const floor = this.parseFloorSpec();
    this.punct(";");
    this.kw("outbound");
    this.punct(":");
    const outbound = this.parsePath();
    this.punct(";");
    this.kw("return");
    this.punct(":");
    const ret = this.parsePath();
    this.punct(";");

    const elements: ElementDecl[] = [];
    while (this.atKw("element")) elements.push(this.parseElement());
    this.punct("}");
    return { floor, outbound, ret, elements };
  }

  private parseFloorSpec(): FloorSpec {
    if (this.atKw("derived")) {
      this.kw("derived");
      this.punct("(");
      const derivedCall = this.ident();
      let derivedArg: string | undefined;
      if (this.at("punct", "(")) {
        this.punct("(");
        derivedArg = this.ident();
        this.punct(")");
      }
      this.punct(")");
      return { derivedCall, derivedArg };
    }
    return { literal: this.quantity() };
  }

  private parsePath(): string[] {
    const path = [this.ident()];
    while (this.at("arrow")) {
      this.eat("arrow");
      path.push(this.ident());
    }
    return path;
  }

  private parseElement(): ElementDecl {
    const t0 = this.kw("element");
    const name = this.ident();
    this.kw("conducts");
    const src = this.ident();
    this.eat("arrow");
    const dst = this.ident();

    let delay: Quantity | undefined;
    let gain = 1.0;
    if (this.atKw("delay")) {
      this.kw("delay");
      delay = this.quantity();
    }
    if (this.atKw("gain")) {
      this.kw("gain");
      gain = this.number();
    }
    this.punct(";");
    return { name, src, dst, delay, gain, span: this.span(t0) };
  }

  private parseEventType(): EventTypeDecl {
    const t0 = this.kw("event");
    this.kw("type");
    const name = this.ident();
    this.punct("=");
    const ctor = this.ident();
    const args: string[] = [];
    if (this.at("punct", "(")) {
      this.punct("(");
      if (!this.at("punct", ")")) {
        args.push(this.ident());
        while (this.at("punct", ",")) {
          this.punct(",");
          args.push(this.ident());
        }
      }
      this.punct(")");
    }
    this.punct(";");
    return { kind: "eventType", name, ctor, args, span: this.span(t0) };
  }

  private parseAntagonist(): AntagonistDecl {
    const t0 = this.kw("antagonist");
    const name = this.ident();
    this.punct("{");
    this.kw("agonist");
    this.punct(":");
    const agonist = this.ident();
    this.punct(";");
    this.kw("antagonist");
    this.punct(":");
    const antagonist = this.ident();
    this.punct(";");
    this.kw("shared");
    this.punct(":");
    const shared = [this.ident()];
    while (this.at("punct", ",")) {
      this.punct(",");
      shared.push(this.ident());
    }
    this.punct(";");
    this.punct("}");
    return { kind: "antagonist", name, agonist, antagonist, shared, span: this.span(t0) };
  }

  private parseExperiment(): ExperimentDecl {
    const t0 = this.kw("experiment");
    const name = this.ident();
    this.punct("{");
    this.kw("intact");
    this.punct(":");
    const intact = this.parseCircuitExpr();
    this.punct(";");

    const lesions: LesionDecl[] = [];
    let observables: Observable[] = [];
    const phases: PhaseDecl[] = [];

    while (!this.at("punct", "}")) {
      if (this.atKw("lesion")) lesions.push(this.parseLesion());
      else if (this.atKw("phase")) phases.push(this.parsePhase());
      else if (this.atKw("observe")) {
        this.kw("observe");
        this.punct(":");
        observables = this.parseObservables();
        this.punct(";");
      } else throw new ParseError("expected lesion, phase, or observe", this.cur);
    }
    this.punct("}");

    if (phases.length && (lesions.length || observables.length)) {
      throw new ParseError("an experiment is either phased or flat, not both", this.cur);
    }
    return { kind: "experiment", name, intact, lesions, observables, phases, span: this.span(t0) };
  }

  private parsePhase(): PhaseDecl {
    const t0 = this.kw("phase");
    const name = this.ident();
    let fromPhase: string | undefined;
    if (this.atKw("from")) {
      this.kw("from");
      fromPhase = this.ident();
    }
    this.punct("{");
    const lesions: LesionDecl[] = [];
    let observables: Observable[] = [];
    while (!this.at("punct", "}")) {
      if (this.atKw("lesion")) lesions.push(this.parseLesion());
      else if (this.atKw("observe")) {
        this.kw("observe");
        this.punct(":");
        observables = this.parseObservables();
        this.punct(";");
      } else throw new ParseError("expected lesion or observe", this.cur);
    }
    this.punct("}");
    return { name, lesions, observables, fromPhase, span: this.span(t0) };
  }

  private parseLesion(): LesionDecl {
    const t0 = this.kw("lesion");
    const name = this.ident();
    this.punct(":");
    const expr = this.parseCircuitExpr();
    this.punct(";");
    return { name, expr, span: this.span(t0) };
  }

  private parseObservables(): Observable[] {
    const obs = [this.parseObservable()];
    while (this.at("punct", ",")) {
      this.punct(",");
      obs.push(this.parseObservable());
    }
    return obs;
  }

  private parseObservable(): Observable {
    const t0 = this.cur;
    const name = this.ident();
    const args: string[] = [];
    if (this.at("punct", "(")) {
      this.punct("(");
      if (!this.at("punct", ")")) {
        args.push(this.ident());
        while (this.at("punct", ",")) {
          this.punct(",");
          args.push(this.ident());
        }
      }
      this.punct(")");
    }
    return { name, args, span: this.span(t0) };
  }

  /** Left-associative chain of postfix lesion operators. */
  private parseCircuitExpr(): CircuitExpr {
    const t0 = this.cur;
    const sp = this.span(t0);
    let expr: CircuitExpr = { op: "ref", name: this.ident(), span: sp };

    while (this.atKw("without", "with", "reroute")) {
      const opTok = this.cur;
      const osp = this.span(opTok);

      if (this.atKw("without")) {
        this.kw("without");
        if (this.atKw("return")) {
          this.kw("return");
          this.punct("(");
          const from = this.ident();
          this.punct(")");
          expr = { op: "withoutReturn", base: expr, from, span: osp };
        } else if (this.atKw("element")) {
          this.kw("element");
          this.punct("(");
          const element = this.ident();
          this.punct(")");
          expr = { op: "withoutElement", base: expr, element, span: osp };
        } else throw new ParseError("expected 'return' or 'element'", this.cur);
      } else if (this.atKw("with")) {
        this.kw("with");
        if (this.atKw("noise")) {
          this.kw("noise");
          this.kw("across");
          const s1 = this.ident() as Stratum;
          this.punct(",");
          const s2 = this.ident() as Stratum;
          this.punct("(");
          const amplitude = this.number();
          this.punct(")");
          expr = { op: "withNoise", base: expr, s1, s2, amplitude, span: osp };
        } else {
          const element = this.ident();
          this.kw("scaling");
          expr = { op: "withScaling", base: expr, element, factor: this.number(), span: osp };
        }
      } else {
        this.kw("reroute");
        this.kw("return");
        this.punct("(");
        const from = this.ident();
        this.punct(")");
        this.kw("through");
        expr = { op: "reroute", base: expr, from, path: this.parsePath(), span: osp };
      }
    }
    return expr;
  }
}

export function parse(src: string): Program {
  return new Parser(tokenize(src)).parseProgram();
}

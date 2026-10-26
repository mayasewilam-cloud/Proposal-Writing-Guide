"""
BioCopilot Scientific Intelligence & Conversational Reasoning Engine.
Powers intelligent, deeply knowledgeable, multi-turn pair-programming & scientific brainstorming.

Core Capabilities:
1. Deep Domain Knowledge Graph (CRISPR, gene therapy, protein expression, kinetics, plastics, isothermal amplification, controls, bioreactors, immunology).
2. Structured Assessment Basis & 5-Tier Evidence Provenance (Detected Task, Relevant Section, Scientific Assumptions, Evidence Status [Evidence-backed | Curated knowledge | General guidance | Unverified | Hypothesis], Key Uncertainty, Recommended Next Step).
3. Conversational Human Tone (warm, rigorous, encouraging, peer-investigator style; never robotic or formulaic).
4. Concrete Experimental Guidance (actual parameters: temperatures, IPTG concentrations, kcat/Km, buffer pH, promoter selection, LoD equations).
5. 1-Click Action & Suggestion Synthesizer (connects directly to proposal draft, aims, methodology, and viva defense).
"""

import re
from typing import Dict, List, Any, Optional

try:
    from core.web_search import execute_multi_search, get_search_engine_links
except ImportError:
    try:
        from web_search import execute_multi_search, get_search_engine_links
    except ImportError:
        execute_multi_search = None
        get_search_engine_links = None

try:
    from .bt301_guide import (
        get_all_chapters,
        get_chapter,
        search_guide,
        get_quick_finder,
        get_sentence_formulation_guide,
        get_glossary_terms,
        get_glossary_term
    )
except (ImportError, ValueError):
    try:
        from core.bt301_guide import (
            get_all_chapters,
            get_chapter,
            search_guide,
            get_quick_finder,
            get_sentence_formulation_guide,
            get_glossary_terms,
            get_glossary_term
        )
    except ImportError:
        try:
            from bt301_guide import (
                get_all_chapters,
                get_chapter,
                search_guide,
                get_quick_finder,
                get_sentence_formulation_guide,
                get_glossary_terms,
                get_glossary_term
            )
        except ImportError:
            get_all_chapters = None
            get_chapter = None
            search_guide = None
            get_quick_finder = None
            get_sentence_formulation_guide = None
            get_glossary_terms = None
            get_glossary_term = None

try:
    from core.paper_summarizer import decode_paper_analyst
except (ImportError, ValueError):
    try:
        from .paper_summarizer import decode_paper_analyst
    except ImportError:
        try:
            from paper_summarizer import decode_paper_analyst
        except ImportError:
            decode_paper_analyst = None


# =============================================================================
# DEEP BIOTECHNOLOGY KNOWLEDGE BASE GRAPH
# =============================================================================
BIO_KNOWLEDGE_GRAPH = {
    "cas12a": {
        "keywords": ["cas12a", "cpf1", "ascas12a", "lbcas12a", "enascas12a", "trans-cleavage", "collateral cleavage", "detectr"],
        "category": "CRISPR Molecular Diagnostics",
        "mechanism": (
            "Cas12a (formerly Cpf1, Class 2 Type V endonuclease) utilizes a single RuvC catalytic domain to recognize a "
            "5'-TTTV-3' PAM (where V = A, C, or G) on the non-target strand, generating a staggered 5-nt 5' overhang. Upon binding "
            "its target dsDNA and forming an R-loop, Cas12a undergoes an allosteric conformational transition that uncages its RuvC "
            "catalytic site. This activates robust, indiscriminate single-stranded DNase (ssDNA) collateral trans-cleavage activity "
            "(kcat ~ 10³ s⁻¹), which cleaves fluorophore-quencher (FQ) ssDNA reporters (e.g. 5'-FAM-TTATT-BHQ1-3') to generate intense "
            "fluorescent or lateral-flow signals within minutes."
        ),
        "lab_parameters": "Operates optimally at 37°C in NEBuffer 2.1 or 1x Cleavage Buffer (50 mM NaCl, 10 mM Tris-HCl, 10 mM MgCl₂, 100 µg/mL BSA, pH 7.9). Requires divalent magnesium (Mg²⁺) for coordinate catalytic positioning.",
        "key_pitfalls": "Humic acids and heavy metals in unpurified environmental wastewater chelate Mg²⁺ and quench FAM fluorescence. High background trans-cleavage occurs if crRNA secondary structures form stable self-hairpins (ΔG < -3.0 kcal/mol).",
        "rescue_protocol": "Pre-treat crude samples with PVPP micro-columns to scavenge humic polyphenols. Add 1% (v/v) formamide or 5% glycerol to relax crRNA hairpins, and re-tile the guide 50 bp downstream if non-target noise exceeds 10% of plateau.",
        "benchmark": "Analytical LoD reaching 1–10 copies/µL when coupled with isothermal RPA or LAMP, with single-nucleotide polymorphism (SNP) discrimination capability."
    },
    "cas13": {
        "keywords": ["cas13", "cas13a", "cas13b", "c2c2", "sherlock", "rna targeting", "hepn"],
        "category": "CRISPR RNA Diagnostics",
        "mechanism": (
            "Cas13 (Class 2 Type VI) contains twin HEPN (Higher Eukaryotes and Prokaryotes Nucleotide-binding) catalytic domains. "
            "Unlike Cas9 or Cas12a which target DNA, Cas13 recognizes single-stranded RNA guided by a ~28-nt spacer with a Protospacer "
            "Flanking Site (PFS; often 3'-H where H = A, U, or C). Target RNA recognition activates indiscriminate ssRNA collateral trans-cleavage, "
            "cleaving fluorescent quenched RNA reporters (e.g. FAM-rUrUrUrUrU-BHQ1) in the SHERLOCK platform."
        ),
        "lab_parameters": "Typically paired with in vitro transcription (T7 RNA polymerase) following RPA or RT-RPA amplification. Operates at 37°C in 20 mM HEPES, 60 mM NaCl, 5 mM MgCl₂, 0.1% Tween-20, pH 7.3.",
        "key_pitfalls": "Endogenous RNases present in human saliva or clinical specimens rapidly degrade both RNA targets and reporter probes, producing massive false-positive background.",
        "rescue_protocol": "Include Murine RNase Inhibitor (0.5 U/µL) or DEPC treatment, and verify baseline integrity using an untransformed wild-type negative control without Cas13 enzyme.",
        "benchmark": "Attomolar sensitivity (down to 2 aM, ~1 copy/µL) capable of resolving RNA virus variants (SARS-CoV-2, Dengue, Zika)."
    },
    "prime_editing": {
        "keywords": ["prime editing", "pe2", "pe3", "pe5", "pegrna", "reverse transcriptase", "split-intein", "twin-pe"],
        "category": "Precision Gene Editing",
        "mechanism": (
            "Prime Editing couples an engineered Moloney Murine Leukemia Virus reverse transcriptase (M-MLV RT) to a Cas9 H840A nickase, "
            "guided by a prime editing guide RNA (pegRNA). The pegRNA possesses an extended 3' tail encoding a Primer Binding Site (PBS, 12–15 nt) "
            "and a Reverse Transcription Template (RTT, 10–16 nt) specifying the intended edit. After Cas9 nicking of the PAM-containing strand, "
            "the 3' flap hybridizes to the PBS, and the fused RT directly copies the new sequence into the genomic target without creating "
            "double-strand DNA breaks (DSBs), thereby bypassing indel-forming non-homologous end joining (NHEJ) and chromosomal translocations."
        ),
        "lab_parameters": "PE3 incorporates an auxiliary sgRNA that nicks the non-edited strand 40–90 bp downstream to bias cellular mismatch repair toward the newly synthesized flap, elevating editing efficiency by 2–4 fold.",
        "key_pitfalls": "Size ceiling: The PE fusion protein is ~6.3 kb, which exceeds the ~4.7 kb packaging ceiling of single Adeno-Associated Virus (AAV) capsids. Mismatch repair (MMR) proteins (MSH2/MSH6) actively dismantle prime edited flaps.",
        "rescue_protocol": "Deploy a Dual-AAV Split-Intein delivery architecture (N-terminal Cas9 nickase + C-terminal RT with split Nostoc punctiforme inteins), or encapsulate PE mRNA and synthetic pegRNA in bone-marrow-targeted Lipid Nanoparticles (tLNPs).",
        "benchmark": "20–60% targeted point mutation or small indel correction with <1% unintended bystander indels."
    },
    "base_editing": {
        "keywords": ["base editing", "base editor", "abe", "abe8e", "cbe", "be4", "adenine deaminase", "cytidine deaminase"],
        "category": "Precision Gene Editing",
        "mechanism": (
            "Base editors fuse an evolved deaminase (such as TadA-8e for Adenine Base Editors [ABEs] or APOBEC1/rAPOBEC1 for Cytidine Base Editors [CBEs]) "
            "to a catalytically impaired Cas9 nickase (D10A). Guided by an sgRNA, the deaminase acts on single-stranded DNA within an editing window "
            "(typically protospacer positions 4–8 counting the PAM as 21–23), converting C•G to T•A or A•T to G•C without requiring a donor template or "
            "generating double-strand DNA breaks."
        ),
        "lab_parameters": "ABE8e exhibits an extraordinary acceleration in deamination kinetics (~1000-fold faster than ABE7.10), enabling robust editing in post-mitotic cells and primary hematopoietic stem cells (HSPCs).",
        "key_pitfalls": "Bystander editing: If multiple target bases (e.g. two adenines) exist within the 4–8 editing window, both may be deaminated indiscriminately. Transcriptome-wide RNA off-target deamination has been observed with early CBE variants.",
        "rescue_protocol": "Use engineered narrow-window editors (e.g. ABE8e with V106W mutation) or swap PAM variants (SpG, SpRY, NG-Cas9) to shift the editing frame such that only the single pathogenic nucleotide occupies the active catalytic pocket.",
        "benchmark": "Achieves >70% on-target editing in CD34+ HSPCs (e.g. BCL11A enhancer disruption for Sickle Cell Disease) with <1% indel formation."
    },
    "lnp_delivery": {
        "keywords": ["lnp", "lipid nanoparticle", "tlnp", "ionizable lipid", "sm-102", "alc-0315", "endosomal escape", "peg-lipid"],
        "category": "Non-Viral In Vivo Delivery",
        "mechanism": (
            "Lipid Nanoparticles (LNPs) encapsulate fragile nucleic acids (mRNA, sgRNA, Cas9-RNP) via electrostatic condensation. "
            "A standard formulation comprises four precisely balanced lipids: 1) Ionizable cationic lipid (e.g. SM-102, ALC-0315, ~50 mol%), "
            "which remains neutral at physiological pH 7.4 (avoiding systemic toxicity) but protonates in acidic endosomes (pH 5.5–6.0) to disrupt the "
            "endosomal membrane via inverted hexagonal (H_II) phase transitions; 2) Helper phospholipid (DSPC, ~10 mol%) providing structural bilayer stability; "
            "3) Cholesterol (~38.5 mol%) modulating membrane fluidity and packing; and 4) PEGylated lipid (PEG2000-DMG, ~1.5 mol%) preventing particle aggregation "
            "and reducing serum opsonization."
        ),
        "lab_parameters": "Formulated via microfluidic staggered herringbone mixing of ethanolic lipid phase with aqueous acidic RNA phase (50 mM citrate, pH 4.0) at a 1:3 volume ratio and nitrogen/phosphate (N/P) ratio of 6:1, followed by dialysis into PBS pH 7.4. Target hydrodynamic diameter: 70–90 nm, polydispersity index (PDI) < 0.1, encapsulation efficiency > 90%.",
        "key_pitfalls": "Default hepatic tropism: Systemic intravenous administration of unfunctionalized LNPs results in spontaneous adsorption of Apolipoprotein E (ApoE), directing >80% of cargo to liver hepatocytes via Low-Density Lipoprotein (LDL) receptors. Extrahepatic tissues (bone marrow, spleen, lung) receive negligible doses.",
        "rescue_protocol": "Incorporate selective organ targeting (SORT) molecules (e.g. 20–50% DOTAP for lung, 10–30% 18:1 PA for spleen), or conjugate high-affinity surface ligands/scFvs (anti-CD117 for bone marrow stem cells, anti-CD3 for T cells).",
        "benchmark": "Enables repeatable non-viral dosing with zero pre-existing neutralizing capsid antibodies."
    },
    "aav_vectors": {
        "keywords": ["aav", "aav9", "aav8", "adeno-associated virus", "viral vector", "capsid", "serotype"],
        "category": "Viral Gene Delivery",
        "mechanism": (
            "Adeno-Associated Virus (AAV) is a non-pathogenic parvovirus possessing a single-stranded DNA genome flanked by inverted terminal repeats (ITRs). "
            "Recombinant AAV (rAAV) replaces rep and cap genes with the therapeutic transgene cassette. Capsid serotypes display distinct cell-surface receptor "
            "tropisms (AAV9 crosses the blood-brain barrier and transduces cardiomyocytes/skeletal muscle; AAV8 selectively targets hepatocytes; AAV2 transduces retinal cells)."
        ),
        "lab_parameters": "Packaged via triple transfection in suspension HEK293 (transgene plasmid + pAAV-RC packaging plasmid + pHelper providing adenoviral E2A/E4/VA genes). Purified by iodixanol gradient ultracentrifugation and validated by ddPCR genomic titer (>10¹² vg/mL).",
        "key_pitfalls": "Strict packaging capacity limit of ~4.7 kb between ITRs (attempts to package >5.0 kb cause genome truncation). 30–70% of human populations carry pre-existing neutralizing antibodies that completely neutralize therapeutic capsids. Re-dosing is blocked by high-titer anti-AAV IgG.",
        "rescue_protocol": "For oversized cargos (>5 kb), use dual-AAV split-intein protein trans-splicing or split-ITR homologous recombination. Pre-screen human cohorts for neutralizing antibody titers (IC50 < 1:5).",
        "benchmark": "FDA-approved clinical standard for monogenic diseases (Luxturna for LCA2 retinal dystrophy, Zolgensma for SMA)."
    },
    "pichia_expression": {
        "keywords": ["pichia", "pichia pastoris", "komagataella phaffii", "aox1", "methanol", "secretion", "alpha-factor"],
        "category": "Eukaryotic Host Chassis",
        "mechanism": (
            "Pichia pastoris (Komagataella phaffii) is a methylotrophic yeast capable of high-density aerobic growth (>100 g/L dry cell weight) "
            "and extracellular protein secretion. Transgenes integrated into the genome behind the Alcohol Oxidase 1 (AOX1) promoter undergo >1000-fold "
            "transcriptional induction upon shifting from glycerol/glucose repression to methanol supplementation. Secretion is driven by the N-terminal "
            "Saccharomyces cerevisiae α-mating factor pre-pro signal peptide, which is cleaved sequentially in the ER and Golgi by signal peptidase and Kex2 protease."
        ),
        "lab_parameters": "Cultivated in BMGY (glycerol accumulation phase, 24–48 h) then switched to BMMY with 0.5–1.0% (v/v) methanol feed every 24 hours at 28–30°C and pH 6.0 with high dissolved oxygen (DO > 20%).",
        "key_pitfalls": "Hyperglycosylation: Unlike mammalian cells which generate complex branched sialylated glycans, Pichia attaches high-mannose chains (30–150 mannose residues) that can shield active sites or trigger immunogenicity. Secreted host proteases (Pep4, Prb1) can degrade target proteins during prolonged fermentation.",
        "rescue_protocol": "Deploy protease-deficient host strains (e.g. SMD1168 or SMD1163) or glycoengineered Pichia strains with humanized N-glycosylation pathways. Lower induction temperature to 20°C and add 1% casamino acids to reduce proteolytic degradation.",
        "benchmark": "Extracellular secretional yields reaching 1–10 g/L with minimal contaminating host proteins, dramatically simplifying downstream chromatography."
    },
    "ecoli_expression": {
        "keywords": ["e. coli", "bl21", "rosetta", "shuffle", "inclusion bodies", "t7", "iptg", "chaperone"],
        "category": "Bacterial Host Chassis",
        "mechanism": (
            "Escherichia coli BL21(DE3) contains the λDE3 lysogen carrying T7 RNA polymerase under the control of the lacUV5 promoter. "
            "Addition of isopropyl β-D-1-thiogalactopyranoside (IPTG) derepresses the lac repressor, triggering rapid T7 transcription of genes cloned "
            "into pET vectors. The BL21 strain is naturally deficient in Lon and OmpT proteases, protecting heterologous proteins from degradation."
        ),
        "lab_parameters": "Grow in LB, 2xYT, or Terrific Broth (TB) at 37°C to mid-log phase (OD600 = 0.6–0.8). Induce with 0.1–0.5 mM IPTG at 16–18°C for 16–20 hours.",
        "key_pitfalls": "Inclusion bodies: Rapid translation at 37°C saturates bacterial chaperone machinery (DnaK-DnaJ-GrpE, GroEL-ES), leading to aggregation of hydrophobic domains into insoluble inclusion bodies. Lack of post-translational modifications and inability to form complex disulfide bonds in reducing cytoplasm.",
        "rescue_protocol": "1) Lower induction temperature to 16°C with 0.1 mM IPTG to slow elongation kinetics; 2) Fuse an N-terminal Maltose-Binding Protein (MBP) or SUMO solubility tag with an HRV-3C cleavage site; 3) Express in SHuffle or Origami strains which possess an oxidizing cytoplasm (trxB/gor double mutants) to promote proper disulfide bond isomerization.",
        "benchmark": "Standard laboratory workhorse yielding 10–50 mg/L of soluble functional enzymes with low capital cost."
    },
    "petase_kinetics": {
        "keywords": ["petase", "mhetase", "ideonella sakaiensis", "plastic degradation", "cutinase", "depolymerization", "glass transition", "tg"],
        "category": "Enzymatic Biocatalysis & Upcycling",
        "mechanism": (
            "Ideonella sakaiensis PETase (IsPETase, EC 3.1.1.101) hydrolyzes the ester bonds of semi-crystalline polyethylene terephthalate (PET), "
            "releasing mono-(2-hydroxyethyl) terephthalate (MHET) as its major intermediate, with trace terephthalic acid (TPA) and bis(2-hydroxyethyl) terephthalate (BHET). "
            "The catalytic mechanism proceeds via a Ser160-His237-Asp206 catalytic triad. A crucial biophysical constraint is that commercial PET has a glass "
            "transition temperature (Tg ≈ 65–70°C), below which the polymer chains remain rigid and tightly packed, dramatically limiting enzyme access. "
            "However, wild-type IsPETase rapidly unfolds and loses activity at temperatures above 37–40°C (melting temperature Tm ≈ 48°C)."
        ),
        "lab_parameters": "Assayed on low-crystallinity amorphous PET coupons or post-consumer PET powder at pH 8.0–9.0 in 50 mM glycine-NaOH buffer. Quantified via reverse-phase HPLC monitoring TPA and MHET release at 240 nm.",
        "key_pitfalls": "Product inhibition: Accumulation of MHET strongly competitively inhibits PETase active sites (Ki ≈ 0.2 mM). Wild-type enzyme undergoes thermal denaturation before reaching polymer softening temperatures.",
        "rescue_protocol": "1) Engineer rational disulfide bonds (e.g. A180C–G165C in DuraPETase or ThermoPETase), raising the melting temperature to Tm ≥ 75°C to operate near the PET Tg; 2) Deploy a dual-enzyme cascade linking PETase to MHETase (via flexible (G4S)3 linkers or co-culture) to rapidly hydrolyze MHET into TPA and ethylene glycol, eliminating product inhibition.",
        "benchmark": "Engineered variants (e.g. LCC-ICCG, DuraPETase) achieve >90% depolymerization of post-consumer PET packaging within 10–24 hours at 65–72°C."
    },
    "isothermal_rpa": {
        "keywords": ["rpa", "recombinase polymerase amplification", "isothermal", "uvsx", "uvsy", "gp32", "bsu", "twistamp"],
        "category": "Point-of-Care Nucleic Acid Amplification",
        "mechanism": (
            "Recombinase Polymerase Amplification (RPA) achieves exponential dsDNA amplification under constant ambient/moderate temperature (37–42°C) "
            "without requiring thermal denaturation. The reaction relies on three core enzymes: 1) T4 bacteriophage recombinase UvsX, which forms a nucleoprotein "
            "filament with oligonucleotide primers (30–35 nt) and facilitates strand invasion into homologous duplex DNA; 2) Recombinase loading factor UvsY; "
            "3) Single-stranded DNA-binding protein gp32, which stabilizes the displaced D-loop strand; and 4) Strand-displacing Bsu or Sau DNA polymerase, "
            "which synthesizes the nascent DNA strand from the free 3'-OH."
        ),
        "lab_parameters": "Runs at 37–39°C for 15–20 minutes. Reaction initiated by addition of 14 mM magnesium acetate. Primers must be 30–35 nucleotides long (longer than standard PCR 20-mers) with GC content 40–60%.",
        "key_pitfalls": "Off-target primer-dimerization and non-specific amplification if primer 3' ends contain palindromic homology. In single-pot RPA-CRISPR assays, active Cas12a will prematurely cleave primer amplicons unless the two reactions are kinetically or physically separated.",
        "rescue_protocol": "Deploy a two-step temperature or physical separation (e.g. pre-amplifying RPA in the tube bottom for 15 min, then centrifuging Cas12a-crRNA from the tube lid), or engineer phosphorothioate-protected primers.",
        "benchmark": "Amplifies single-digit DNA copies to detectable microgram levels in under 20 minutes directly in battery-operated handheld devices."
    },
    "gene_therapy": {
        "keywords": ["gene therapy", "gene editing", "ex vivo", "in vivo gene therapy", "transgene", "crispr medicine", "sickle cell", "casgevy", "monogenic"],
        "category": "Therapeutic Genome Editing & Gene Therapy",
        "mechanism": (
            "Therapeutic genome editing operates primarily through two clinical modalities: Ex Vivo cell therapy "
            "(such as CRISPR-Cas9 disruption of the BCL11A erythroid enhancer in patient-derived CD34+ hematopoietic stem cells "
            "for sickle cell disease and transfusion-dependent beta-thalassemia [Casgevy / exa-cel], followed by myeloablative conditioning "
            "and autologous transplantation) and In Vivo gene delivery (direct systemic or tissue-restricted delivery of recombinant AAV "
            "viral vectors or ionizable lipid nanoparticles [LNPs] carrying mRNA/Cas9-RNP or base editors to liver hepatocytes, CNS, or retinal "
            "pigment epithelium). The core biological hurdle is resolving the triad of delivery tropism, duration of editor expression "
            "(transient vs permanent), and minimizing double-strand break (DSB) consequences such as p53 pathway activation, large chromosomal "
            "deletions (>1 kb), or translocations."
        ),
        "lab_parameters": "Ex vivo electroporation: Lonza 4D-Nucleofector program EO-100 or CA-137 using 2–4 µM Cas9:sgRNA RNP (molar ratio 1:1.2). In vivo LNP formulation: 50 mol% ionizable lipid (SM-102 or ALC-0315) + 10 mol% DSPC + 38.5 mol% cholesterol + 1.5 mol% DMG-PEG2000; N/P ratio 6:1; target hydrodynamic diameter 70–85 nm, PDI < 0.08, encapsulation efficiency > 92%.",
        "key_pitfalls": "Standard Cas9 nuclease generates DNA double-strand breaks (DSBs), inducing non-homologous end joining (NHEJ) which can produce unwanted chromosomal translocations, chromothripsis, and p53-dependent cellular apoptosis. Furthermore, high seroprevalence of pre-existing neutralizing antibodies against AAV capsids (up to 70%) or bacterial Cas9 endonucleases triggers cytotoxic T-lymphocyte (CTL) destruction of edited cells.",
        "rescue_protocol": "1) Transition from DSB nucleases to precision Base Editors (ABE8e / CBE) or Prime Editors (PE3/PEmax) which install transition mutations or small indels without double-strand cleavage; 2) Utilize transient non-viral delivery (LNP-encapsulated mRNA or RNP) to restrict endonuclease half-life to <24 hours, slashing off-target editing by >90% compared to constitutive viral expression; 3) Screen patients for neutralizing antibodies or use synthetic evolved capsids / non-viral targeted LNPs.",
        "benchmark": "Clinical curative thresholds: >70% allelic editing in human CD34+ HSPCs, >40% sustained fetal hemoglobin (HbF) induction in sickle cell patients, and >80% serum LDL-C reduction following single-dose in vivo base editing of PCSK9."
    },
    "car_t_immunotherapy": {
        "keywords": ["car-t", "car t", "chimeric antigen receptor", "immunotherapy", "t cell", "cd19", "scfv", "tcr", "synnotch"],
        "category": "Cellular Immunotherapy & Synthetic Immunology",
        "mechanism": (
            "Chimeric Antigen Receptor (CAR) T-cell therapy reprograms autologous or allogeneic T lymphocytes to eradicate malignant "
            "or autoimmune cells in an MHC-unrestricted manner. A modular synthetic CAR comprises: 1) An extracellular single-chain variable "
            "fragment (scFv) derived from a monoclonal antibody recognizing a tumor-associated surface antigen (e.g. CD19, BCMA, ROR1); "
            "2) A CD8α or IgG4 hinge and transmembrane spacer; 3) An intracellular costimulatory signaling domain (4-1BB/CD137 for prolonged "
            "in vivo persistence and metabolic fitness, or CD28 for rapid, robust effector cytokine burst); and 4) A CD3ζ primary activation "
            "domain harboring immunoreceptor tyrosine-based activation motifs (ITAMs)."
        ),
        "lab_parameters": "Primary human CD3+ T cells isolated from peripheral blood mononuclear cells (PBMCs), activated with anti-CD3/CD28 magnetic dynabeads for 24–48 h, transduced with lentivirus (MOI 3–5) or edited via CRISPR-Cas9 knock-in into the TRAC locus using AAV6 donor repair templates, and expanded in serum-free medium supplemented with recombinant human IL-7 and IL-15 (each 5–10 ng/mL) for 7–10 days in gas-permeable rocking bioreactors.",
        "key_pitfalls": "Severe systemic toxicities including Cytokine Release Syndrome (CRS, driven by IL-6, IL-1, and TNF-α) and Immune Effector Cell-Associated Neurotoxicity Syndrome (ICANS); continuous antigen stimulation leading to T-cell exhaustion (upregulation of PD-1, TIM-3, LAG-3); and lethal on-target off-tumor toxicity when antigens are shared with healthy vital tissues.",
        "rescue_protocol": "1) Knock the CAR directly into the T-cell receptor alpha constant (TRAC) locus under endogenous transcriptional promoter regulation to prevent tonic signaling and delay exhaustion; 2) Implement Boolean logic gates (e.g. dual-receptor synNotch circuits requiring Antigen A AND Antigen B, or inhibitory CARs [iCAR] with PD-1 signaling to spare normal cells); 3) Integrate an inducible safety kill-switch (inducible caspase-9 [iCasp9] activated by small-molecule dimerizer AP1903 / rimiducid).",
        "benchmark": ">80% complete remission rates in relapsed/refractory B-cell acute lymphoblastic leukemia (B-ALL) and durable multi-year memory stem T-cell (T_SCM) persistence."
    },
    "mrna_vaccine": {
        "keywords": ["mrna vaccine", "mrna", "vaccine", "pseudouridine", "cap1", "antigen", "cleancap", "poly(a)"],
        "category": "Synthetic RNA Therapeutics & Vaccines",
        "mechanism": (
            "Synthetic messenger RNA (mRNA) vaccines deliver the genetic code for a pathogenic antigen directly to host cellular translational machinery. "
            "High in vivo translation and minimal immunogenic reactogenicity are achieved through four biochemical pillars: 1) Enzymatic or co-transcriptional "
            "Cap-1 structure (e.g. CleanCap AG) providing high affinity for eukaryotic initiation factor 4E (eIF4E) and resisting decapping enzymes; "
            "2) 100% stoichiometric substitution of uridine with N1-methylpseudouridine (m1Ψ), which prevents recognition by intracellular pattern recognition "
            "receptors (TLR3, TLR7, TLR8, and RIG-I), preventing type I interferon-mediated translational shutdown; 3) Codon-optimized open reading frame "
            "enriched in high-abundance human tRNA codons; and 4) A polyadenylated tail (100–120 nt) binding Poly(A)-Binding Protein (PABP) for circularized "
            "translation initiation."
        ),
        "lab_parameters": "Synthesized via in vitro transcription (IVT) using T7 RNA polymerase from linearized plasmid DNA at 37°C for 2 h. Purified by cellulose chromatography or hydrophobic interaction chromatography (HIC) to eliminate double-stranded RNA (dsRNA) transcriptional run-on byproducts. Encapsulated in 4-component ionizable lipid nanoparticles at an N/P ratio of 6:1.",
        "key_pitfalls": "Double-stranded RNA (dsRNA) contaminants generated by T7 RNA polymerase run-on transcription trigger intracellular MDA5 and PKR sensors, activating RNase L and extinguishing antigen expression. Hydrolytic cleavage of the RNA phosphodiester backbone at ambient temperatures requires strict ultra-cold storage (-80°C).",
        "rescue_protocol": "1) Run cellulose spin-column chromatography or reverse-phase HPLC post-IVT to quantitatively scavenge dsRNA contaminants to undetectable levels (<0.001%); 2) Engineer lyophilized formulations incorporating 10% (w/v) trehalose or sucrose excipients, enabling ambient room-temperature stability for >6 months.",
        "benchmark": ">90% protective clinical efficacy against respiratory pathogens (SARS-CoV-2, RSV, Influenza) with balanced neutralizing antibody titers (>10³ GMT) and robust Th1 CD4+/CD8+ cytotoxic cellular immunity."
    },
    "phage_therapy": {
        "keywords": ["phage", "bacteriophage", "phage therapy", "endolysin", "superbug", "antimicrobial resistance", "amr"],
        "category": "Precision Antimicrobial Biotherapeutics",
        "mechanism": (
            "Phage therapy harnesses obligately lytic bacteriophages or their recombinant lytic enzymes (endolysins) to eradicate multi-drug resistant "
            "(MDR) bacterial superbugs. Phage infection begins when tail fibers bind with exquisite specificity to surface receptors (lipopolysaccharide, "
            "outer membrane proteins like OmpA, teichoic acids, or type IV pili). Phages inject their genomic DNA/RNA, shut down host transcription, "
            "replicate within 20–40 minutes, and trigger coordinated host lysis via holin (which perforates the inner cell membrane) and endolysin "
            "(peptidoglycan hydrolase that degrades the cell wall peptidoglycan). Recombinant endolysins can also be applied externally ('enzybiotics'), "
            "lysing Gram-positive bacteria within seconds without needing viral replication."
        ),
        "lab_parameters": "Propagated in mid-log phase host cultures (OD600 = 0.4–0.6), harvested post-complete lysis, and clarified by tangential flow filtration (0.22 µm). Purified by CsCl density gradient centrifugation or octyl glucoside extraction to achieve clinical endotoxin levels < 5.0 Endotoxin Units (EU)/mL. Titrated via double-layer agar overlay plaque assay (PFU/mL, target > 10¹⁰ PFU/mL).",
        "key_pitfalls": "Rapid emergence of bacterial resistance via loss or mutation of phage surface receptors, CRISPR-Cas bacterial adaptive immunity, or restriction-modification systems. Narrow host range limits efficacy against heterogeneous bacterial strains. Endotoxin contamination in crude lysates triggers septic shock.",
        "rescue_protocol": "1) Formulate a multi-phage cocktail (3–5 diverse phages targeting orthogonal surface receptors, e.g. LPS, OmpC, and flagella simultaneously); 2) Leverage phage-antibiotic synergy (PAS): sub-inhibitory doses of antibiotics induce bacterial filamentation and accelerate phage burst size; 3) Deploy recombinant chimeric endolysins with swapped cell-wall binding domains (CBDs).",
        "benchmark": "Achieves rapid 4–6 log₁₀ CFU/mL reduction in multi-drug resistant ESKAPE pathogens (Pseudomonas aeruginosa, Acinetobacter baumannii, Klebsiella pneumoniae, MRSA) within hours while completely sparing the commensal human gut microbiome."
    },
    "bioremediation_synthetic_biology": {
        "keywords": ["bioremediation", "degradation", "biodegradation", "heavy metal", "pfas", "pollutant", "microbial fuel cell", "biosensor"],
        "category": "Environmental Biotechnology & Synthetic Biology",
        "mechanism": (
            "Synthetic environmental biotechnology reprograms microbial chassis (such as Pseudomonas putida KT2440, Rhodococcus erythropolis, "
            "or Bacillus subtilis) or cell-free enzymatic cascades to mineralize persistent environmental xenobiotics (aromatic hydrocarbons, PFAS, "
            "pesticides, endocrine disruptors) or sequester heavy metals (Pb²⁺, Cd²⁺, As³⁺). Catabolic pathways are engineered through multi-gene synthetic "
            "operons expressing monooxygenases, dioxygenases, and ring-cleavage hydrolases under inducible or constitutive promoters. Heavy metal "
            "bioaccumulation utilizes surface display of cysteine-rich phytochelatins or metallothioneins, while whole-cell biosensors couple allosteric "
            "transcription factors (e.g. ArsR, CadC) to fluorescent or electrochemical reporters."
        ),
        "lab_parameters": "Cultivated in minimal salt medium (M9 or Bushnell-Haas) with target pollutant as sole carbon/energy source. Bioreactors operate under controlled dissolved oxygen (DO > 25%), neutral pH 6.8–7.4, and balanced macronutrient stoichiometry (C:N:P = 100:10:1). Catalytic degradation quantified via Gas Chromatography-Mass Spectrometry (GC-MS) or HPLC.",
        "key_pitfalls": "Severe metabolic burden and growth defects in non-sterile field conditions; competitive displacement by native environmental microflora; toxic intermediate metabolite accumulation; and strict regulatory barriers prohibiting the release of living Genetically Modified Organisms (GMOs) into open ecosystems.",
        "rescue_protocol": "1) Integrate synthetic biocontainment kill-switches (e.g. mazEF toxin-antitoxin circuits, temperature-sensitive repressors, or synthetic auxotrophy requiring non-canonical amino acids like 4-aminophenylalanine); 2) Pivot to Acellular / Cell-Free Enzyme Cascades immobilized on porous silica or magnetic nanoparticles, which deliver identical catalytic degradation without releasing living GMOs.",
        "benchmark": ">85% mineralization of target xenobiotics in continuous-flow reactor systems within 24–48 hours, with validated synthetic biocontainment escape frequencies < 10⁻⁸."
    },
    "controls_and_validation": {
        "keywords": ["controls", "negative control", "positive control", "triplicate", "lod", "probit", "iac", "clsi", "sem"],
        "category": "Experimental Rigor & Assay Validation",
        "mechanism": (
            "Scientific proposals must declare a comprehensive control matrix to satisfy grant review committees (STDF, ICGEB, NIH, NSF): "
            "1) Untransformed Wild-Type / Vehicle Negative Control: Cells harboring the empty plasmid vehicle, untransformed host chassis, or solvent vehicle (e.g. 0.1% DMSO) subjected to identical assay conditions to establish physiological background baseline; "
            "2) Internal Amplification / Reference Control (IAC): A non-target sequence or housekeeping gene co-amplified in the same reaction to prove that negative results are genuine rather than enzyme inhibition; "
            "3) Positive Reference Standard: High-purity synthetic target, commercial enzyme, or reference drug titrated across serial dilutions; "
            "4) Biological vs. Technical Replicates: Independent biological replicates (separate cultures/passages, typically n >= 3 based on expected effect size and variance) and technical replicates (triplicate wells) analyzed via Student's t-test or one-way ANOVA."
        ),
        "lab_parameters": "Limit of Detection (LoD) is typically determined via Probit regression analysis at the 95% confidence interval (CLSI EP17-A2) or 3.3 * (SD_blank / Slope) for linear calibration curves.",
        "key_pitfalls": "Relying on pure water/buffer as the sole negative control fails to capture biological matrix autofluorescence, solvent toxicity, or endogenous background activity.",
        "rescue_protocol": "Prepare matrix-matched negative controls (e.g. blank biological matrix or empty-vector lysate) and establish quantitative cutoffs (Mean_negative + 3*SD_negative).",
        "benchmark": "Satisfies CLSI EP17-A2 / ICH Q2(R2) analytical validation guidelines [Curated Knowledge Base]."
    },
    "pcr_qpcr_amplification": {
        "keywords": ["pcr", "qpcr", "rt-qpcr", "rt-pcr", "taqman", "sybr", "sybr green", "ct value", "melt curve", "primer", "primers", "thermal cycling", "ddpcr", "2^-ddct", "delta delta ct"],
        "category": "Molecular Diagnostics & Gene Expression (PCR / RT-qPCR)",
        "mechanism": (
            "Polymerase Chain Reaction (PCR) exponentially amplifies specific DNA targets across thermal cycles of denaturation (94–98°C), "
            "primer annealing (55–65°C), and polymerase extension (72°C). Quantitative real-time PCR (qPCR / RT-qPCR) monitors amplification kinetics "
            "using sequence-specific hydrolysis probes (TaqMan) or dsDNA-intercalating fluorophores (SYBR Green I). Relative gene expression is quantified "
            "via the Livak 2^(-ΔΔCt) method normalized against validated endogenous housekeeping genes (GAPDH, ACTB, 16S rRNA)."
        ),
        "lab_parameters": "Typical reported protocol: Primers (18–24 nt, 40–60% GC, Tm 58–62°C, amplicon 70–200 bp). Standard curve across 5–6 log10 serial dilutions must show amplification efficiency E = 90–110% (slope -3.1 to -3.6, R² >= 0.99) per MIQE guidelines.",
        "key_pitfalls": "Primer-dimer artifacts generating false-positive SYBR Green signals; genomic DNA (gDNA) contamination in RNA preps; PCR inhibitors shifting Ct values.",
        "rescue_protocol": "1) Include No-Template Controls (NTC) and No-Reverse-Transcriptase (-RT) controls after DNase I treatment; 2) Run melt-curve analysis (65°C to 95°C) to verify a single amplicon peak; 3) Switch to TaqMan hydrolysis probes.",
        "benchmark": "MIQE-compliant dynamic range of 6–7 logs with amplification efficiency 90–110% and NTC Ct > 38 [Curated Knowledge Base]."
    },
    "elisa_western_immunoassay": {
        "keywords": ["elisa", "western blot", "immunoblot", "sds-page", "antibody", "monoclonal", "polyclonal", "horseradish peroxidase", "hrp", "tmb", "chemiluminescence", "coomassie", "bradford", "bca"],
        "category": "Immunoassays & Protein Verification (ELISA / Western Blot / SDS-PAGE)",
        "mechanism": (
            "SDS-PAGE denatures proteins with sodium dodecyl sulfate to separate polypeptides strictly by molecular weight (kDa). "
            "Western blotting electrotransfers separated proteins onto PVDF or nitrocellulose membranes for specific immunodetection. "
            "Sandwich ELISA immobilizes capture antibodies on 96-well plates to quantify soluble antigens (e.g. cytokines TNF-α, IL-6) via enzymatic TMB turnover at OD 450 nm."
        ),
        "lab_parameters": "Typical reported range: Blocking with 5% non-fat milk or 3% BSA in TBST (0.1% Tween-20). Fit ELISA standard curves using 4-Parameter Logistic (4PL) nonlinear regression.",
        "key_pitfalls": "Non-specific cross-reactivity of polyclonal antibodies; uneven lane loading in Western blots; hook effect at excessive antigen concentrations.",
        "rescue_protocol": "1) Normalize total protein loading via BCA or Bradford assay and verify equal loading using housekeeping controls (β-actin, GAPDH); 2) Include isotype-matched IgG negative control and blank lysate.",
        "benchmark": "Sandwich ELISA typical analytical sensitivity of 5–50 pg/mL with intra-assay CV < 10% [Curated Knowledge Base]."
    },
    "antioxidant_antiinflammatory_assays": {
        "keywords": ["dpph", "abts", "frap", "antioxidant", "free radical", "ic50", "ros", "dcfh-da", "anti-inflammatory", "inflammation", "raw 264.7", "macrophage", "lps", "griess", "nitric oxide", "tnf-alpha", "il-6", "nf-kb", "cox-2"],
        "category": "Bioactivity Screening: Antioxidant & Anti-Inflammatory Assays",
        "mechanism": (
            "Chemical antioxidant assays (DPPH at 517 nm, ABTS at 734 nm, FRAP at 593 nm) measure cell-free radical scavenging. "
            "However, chemical radical scavenging does NOT prove cellular anti-inflammatory activity. Cellular anti-inflammatory validation requires "
            "LPS-stimulated macrophages (RAW 264.7 or THP-1), quantifying nitric oxide (Griess assay at 540 nm) and pro-inflammatory cytokines (TNF-α, IL-6, IL-1β via ELISA/RT-qPCR) alongside MTT cell viability."
        ),
        "lab_parameters": "Typical example protocol: Serial 2-fold dilutions (3.125 to 200 µg/mL) incubated 30 min in dark for DPPH, or 24h in LPS-stimulated (1 µg/mL) macrophages. Derive IC50 via 4-parameter nonlinear regression.",
        "key_pitfalls": "Claiming anti-inflammatory efficacy when the methodology only performs a chemical DPPH assay; mistaking cytotoxicity for anti-inflammatory inhibition.",
        "rescue_protocol": "1) Pair macrophage inflammation assays with an MTT/CCK-8 cell viability screen (restricting to doses with >85% viability); 2) Include matched positive standards (Ascorbic acid/Trolox for DPPH; Dexamethasone for LPS inflammation) and vehicle negative controls.",
        "benchmark": "Dose-dependent IC50 with 95% confidence intervals benchmarked against Ascorbic Acid or Dexamethasone at non-cytotoxic doses [Curated Knowledge Base]."
    },
    "antimicrobial_susceptibility_testing": {
        "keywords": ["antibacterial", "antimicrobial", "antifungal", "mic", "mbc", "broth microdilution", "disk diffusion", "kirby-bauer", "zone of inhibition", "mcfarland", "time-kill", "biofilm", "crystal violet", "checkerboard", "fici"],
        "category": "Microbiology & Antimicrobial Susceptibility (MIC / MBC / Biofilm)",
        "mechanism": (
            "Antimicrobial potency is quantified via standardized CLSI M07/M100 protocols. Broth Microdilution in cation-adjusted Mueller-Hinton Broth (CAMHB) "
            "determines Minimum Inhibitory Concentration (MIC, lowest concentration preventing visible growth at OD600) and Minimum Bactericidal Concentration (MBC, >=99.9% CFU/mL kill)."
        ),
        "lab_parameters": "Standardized inoculum: 0.5 McFarland (~1.5 x 10^8 CFU/mL), diluted in CAMHB to ~5 x 10^5 CFU/mL across 2-fold serial dilutions, incubated at 35±2°C for 16–20 hours.",
        "key_pitfalls": "Using unstandardized bacterial inoculum density; relying solely on agar diffusion for hydrophobic compounds or nanoparticles.",
        "rescue_protocol": "Standardize inoculum at OD600 (0.08–0.13) and include CLSI reference strains (E. coli ATCC 25922, S. aureus ATCC 25923), a positive antibiotic standard (Ciprofloxacin/Gentamicin), sterile broth blank, and vehicle control (<=1% DMSO).",
        "benchmark": "CLSI M07-compliant MIC/MBC determination with MBC/MIC ratio <= 4 indicating bactericidal mechanism [Curated Knowledge Base]."
    },
    "chromatography_enzyme_kinetics": {
        "keywords": ["ni-nta", "imac", "his-tag", "histidine tag", "imidazol", "imidazole", "size exclusion", "sec", "fplc", "hplc", "ion exchange", "michaelis-menten", "km", "kcat", "vmax", "lineweaver-burk", "specific activity"],
        "category": "Downstream Protein Purification & Michaelis-Menten Kinetics",
        "mechanism": (
            "Immobilized Metal Affinity Chromatography (IMAC / Ni-NTA) purifies His6-tagged proteins via coordination bonding with chelated Ni²⁺, "
            "followed by imidazole elution and Size-Exclusion Chromatography (SEC). Enzyme kinetics are determined by fitting initial velocity v0 vs [S] "
            "to the Michaelis-Menten equation v0 = (Vmax[S])/(Km + [S]) to derive Km, Vmax, kcat, and kcat/Km."
        ),
        "lab_parameters": "Typical IMAC protocol: Wash buffer with 20–40 mM imidazole, 300 mM NaCl, pH 7.4–8.0; elution at 250–500 mM imidazole followed by immediate buffer exchange/dialysis.",
        "key_pitfalls": "Using linear Lineweaver-Burk plots as the sole fitting method; leaving high imidazole in the enzyme buffer during kinetic assays.",
        "rescue_protocol": "Desalt fractions via PD-10 column or dialysis, verify >90% monomeric purity via SDS-PAGE/SEC, and fit non-linear Michaelis-Menten regression alongside heat-inactivated enzyme negative controls.",
        "benchmark": "Electrophoretic homogeneity (>90% purity by SDS-PAGE), Purification Table, and non-linear Km, kcat, kcat/Km ± SEM [Curated Knowledge Base]."
    },
    "nanoparticle_drug_delivery": {
        "keywords": ["nanoparticle", "nanoparticles", "liposome", "liposomes", "plga", "chitosan", "hydrogel", "topical", "formulation", "dls", "zeta potential", "pdi", "polydispersity", "encapsulation efficiency", "drug release", "franz diffusion"],
        "category": "Nanobiotechnology, Formulation & Drug Delivery Systems",
        "mechanism": (
            "Nanocarriers (LNPs, liposomes, PLGA/chitosan NPs, hydrogels) protect payloads and govern release kinetics. "
            "Physicochemical quality is characterized by Dynamic Light Scattering (DLS) hydrodynamic diameter, Polydispersity Index (PDI), "
            "Zeta potential, and Encapsulation Efficiency (%EE)."
        ),
        "lab_parameters": "Typical target ranges: Hydrodynamic diameter 50–200 nm; PDI < 0.25 indicating monodisperse colloidal distribution; Zeta potential > +30 mV or < -30 mV for electrostatic stability.",
        "key_pitfalls": "Failing to separate unencapsulated free drug via ultrafiltration before measuring %EE; claiming in vivo healing when only performing in vitro release.",
        "rescue_protocol": "Quantify %EE via centrifugal ultrafiltration (10–30 kDa MWCO) + HPLC/UV-Vis, and evaluate in vitro release kinetics fitted to Higuchi or Korsmeyer-Peppas models alongside blank unloaded vehicle nanoparticles.",
        "benchmark": "Monodisperse colloidal formulation (PDI < 0.25), %EE > 75–85%, and TEM/SEM morphological verification [Curated Knowledge Base]."
    },
        "usp_ansoff_market": {
        "keywords": ["usp", "unique selling", "value proposition", "ansoff", "competitive advantage", "incumbent", "strawman competitor", "market penetration", "product development", "market development", "diversification", "selling points"],
        "category": "Unique Selling Points (USPs) & Ansoff Strategic Positioning",
        "mechanism": (
            "A biotechnology Unique Selling Point (USP) establishes quantifiable technical and translational superiority over a named commercial or clinical benchmark. "
            "It directly precedes and dictates the Ansoff Matrix (Market Penetration, Product Development, Market Development, Diversification)."
        ),
        "lab_parameters": "Winning 3-Part Formula: 'Unlike [Commercial Benchmark], our [Bio-Engineered Tool/Formulation] [Mechanistic Advantage], achieving [Quantifiable Metric] and providing [Clinical/Industrial Stakeholder Benefit].'",
        "key_pitfalls": "Using vague strawman phrases like 'unlike traditional methods'; omitting a quantified margin of superiority; declaring Diversification without recognizing extreme technological and market risk.",
        "rescue_protocol": "Replace strawman terms with exact standards (e.g., 'broth microdilution AST', 'TaqMan RT-qPCR', 'topical hydrocortisone 1%') and map the innovation into the appropriate Ansoff quadrant based on technology novelty and target market novelty.",
        "benchmark": "Named real-world competitor, single-sentence winning USP formula, and justified Ansoff quadrant positioning [Curated Knowledge Base]."
    },
    "swot_pestel_egp_budget": {
        "keywords": ["swot", "pestel", "trl", "technology readiness", "stdf", "asrt", "egp", "budget justification", "consumables", "contingency budget"],
        "category": "Strategic Analysis (SWOT / PESTEL) & Egyptian STDF Budgeting (EGP)",
        "mechanism": (
            "SWOT separates Internal project attributes (Strengths & Weaknesses) from External factors (Opportunities & Threats). "
            "PESTEL evaluates macro-level Political, Economic, Social, Technological, Environmental, and Legal/Biosafety factors. "
            "Section 9 Budget Justification links every consumable and service item to Section 4 methods in Egyptian Pounds (EGP / ج.م)."
        ),
        "lab_parameters": "Early-stage academic proposals span TRL 1–4 (TRL 3: Experimental proof-of-concept; TRL 4: Lab validation in relevant mimic matrix).",
        "key_pitfalls": "Mixing internal weaknesses with external threats in SWOT; quoting budget items in foreign currency without EGP synchronization.",
        "rescue_protocol": "Synchronize Section 9.1 Budget Justification directly with the Section 9.2 Itemized EGP Table and include a justified 5–10% local procurement contingency.",
        "benchmark": "100% alignment between Section 4 Methods, Section 8 Gantt Milestones, and Section 9 Itemized EGP Budget [Curated Knowledge Base]."
    }
}


# =============================================================================
# SOCRATIC REASONING & CO-THINKING ENGINE
# =============================================================================

def detect_primary_concept(text: str) -> Optional[Dict[str, Any]]:
    """Identifies the scientific concept matching the user's inquiry."""
    lower = text.lower()
    for key, data in BIO_KNOWLEDGE_GRAPH.items():
        for kw in data["keywords"]:
            # Word boundary matching
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                return {**data, "key": key}
    return None


def extract_scientific_entities(text: str) -> Dict[str, List[str]]:
    """Extracts biological entities, methods, and parameters from student query."""
    entities = {
        "organisms": [],
        "tools": [],
        "targets": [],
        "methods": []
    }
    lower = text.lower()

    organisms_map = {
        "e. coli": "Escherichia coli BL21(DE3)",
        "pichia": "Pichia pastoris (Komagataella phaffii)",
        "yeast": "Saccharomyces cerevisiae / Pichia",
        "hek293": "Human Embryonic Kidney 293 (HEK293)",
        "cho": "Chinese Hamster Ovary (CHO)",
        "pseudomonas": "Pseudomonas putida KT2440",
        "rhizobium": "Rhizobium leguminosarum",
        "bacillus": "Bacillus subtilis / velezensis"
    }
    for k, v in organisms_map.items():
        if k in lower:
            entities["organisms"].append(v)

    tools_map = {
        "cas12a": "CRISPR-Cas12a (Cpf1)",
        "cas9": "CRISPR-Cas9",
        "cas13": "CRISPR-Cas13 (SHERLOCK)",
        "base editor": "Adenine / Cytidine Base Editor",
        "prime editor": "Prime Editor (PE2/PE3/pegRNA)",
        "petase": "Engineered Ideonella sakaiensis PETase",
        "cutinase": "Leaf-branch compost cutinase (LCC)",
        "lnp": "Targeted Lipid Nanoparticle (tLNP)",
        "aav": "Adeno-Associated Virus (AAV)",
        "car-t": "Chimeric Antigen Receptor T-cell (CAR-T)"
    }
    for k, v in tools_map.items():
        if k in lower:
            entities["tools"].append(v)

    methods_map = {
        "rpa": "Recombinase Polymerase Amplification (RPA)",
        "lamp": "Loop-Mediated Isothermal Amplification (LAMP)",
        "pcr": "Quantitative PCR (qPCR)",
        "sds-page": "SDS-PAGE & Western Blotting",
        "probit": "Probit Regression LoD Analysis",
        "hplc": "High-Performance Liquid Chromatography (HPLC)",
        "ddpcr": "Droplet Digital PCR (ddPCR)"
    }
    for k, v in methods_map.items():
        if k in lower:
            entities["methods"].append(v)

    return entities


def generate_socratic_thinking_response(
    user_query: str,
    active_proposal_context: Dict[str, Any] = None,
    chat_history: List[Dict[str, Any]] = None,
    proposal_context: Dict[str, Any] = None,
    context: Dict[str, Any] = None,
    history: List[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    active_proposal_context = active_proposal_context or proposal_context or context or {}
    proposal_context = active_proposal_context
    context = active_proposal_context
    chat_history = chat_history or history or []
    """
    Synthesizes a deep, articulate, Socratic response that reasons step-by-step
    through the scientific problem, avoiding robotic repetition.
    """
    text = user_query.strip()
    lower = text.lower()
    
    # 1. Check for recognized scientific concept in Knowledge Graph
    matched_concept = detect_primary_concept(text)
    entities = extract_scientific_entities(text)
    
    # Context values from active proposal
    live_title = active_proposal_context.get("title", "")
    live_chassis = active_proposal_context.get("chassis", "")
    live_tool = active_proposal_context.get("tool", "")
    live_target = active_proposal_context.get("target", "")

    # Thinking trace (for transparency and intellectual rigor)
    thinking_steps = []

    clean_trim = re.sub(r'[!?.,]', '', lower).strip()
    
    # Paper Decoder (Scientific Analyst Mode) Intent
    paper_prefix_match = re.search(r'^(?:decode\s+paper|paper\s+decoder|paper\s+decode|analyze\s+paper|deconstruct\s+paper):\s*(.*)', text, re.I | re.DOTALL)
    is_explicit_paper_decode = bool(paper_prefix_match)
    is_paper_decode_intent = bool(re.search(
        r'\b(decode\s+(this\s+)?paper|paper\s+decoder|analyze\s+(this\s+)?paper|deconstruct\s+(this\s+)?paper|evidence\s+extraction\s+(from\s+)?paper|break\s+down\s+(this\s+)?paper)\b',
        lower
    )) and (len(text.split()) >= 15 or bool(re.search(r'\b10\.\d{4,9}/', text)))
    is_paper_decoder = is_explicit_paper_decode or is_paper_decode_intent

    # Web & multi-engine search intent
    search_prefix_match = re.search(r'^(search|find|lookup|look up|google|websearch|web search|scholar):\s*(.*)', text, re.I)
    is_explicit_search = bool(search_prefix_match)
    is_web_search_intent = bool(re.search(r'\b(search (the )?(web|internet|google|online|duckduckgo|engines?)|look up (online|on the web|on google)|search engine|search engines|find (me )?(papers|studies|articles) online|find online|latest (news|research|paper|development) on)\b', lower))
    is_web_search = is_explicit_search or is_web_search_intent

    # BT301 Pedagogical, Writing & Sentence Formulation Intents
    is_sentence_coach = bool(re.search(
        r'\b(formulate\s+(a\s+)?sentence|sentence\s+formulation|how\s+to\s+formulate\s+(a\s+)?sentence|'
        r'build(ing)?\s+(a\s+)?sentence|sentence\s+structure|how\s+to\s+write\s+(a\s+)?sentence|'
        r'write\s+(a\s+)?sentence|sentence\s+guide|sentence\s+blueprint|scientific\s+verbs?|'
        r'active\s+vs\s+passive|active\s+passive|tense\s+in\s+proposal|verb\s+choice|verb\s+matrix|'
        r'informal\s+to\s+academic|hedging|sentence\s+starter)\b',
        lower
    )) or (bool(re.search(r'\b(sentence|sentences)\b', lower)) and bool(re.search(r'\b(formulate|build|write|guide|help|structure|craft)\b', lower)))

    is_hypothesis_coach = bool(re.search(
        r'\b(how\s+to\s+write\s+(a\s+)?hypothesis|write\s+(a\s+)?hypothesis|hypothesis\s+sentence|'
        r'formulate\s+(a\s+)?hypothesis|mechanistic\s+hypothesis|testable\s+hypothesis|'
        r'hypothesis\s+formulation|hypothesis\s+blueprint)\b',
        lower
    ))

        # NEW: Unique Selling Points (USPs) & Ansoff Matrix Coaching Intent (Chapter 25)
    is_usp_coach = bool(re.search(
        r'\b(unique\s+selling(\s+points?|\s+propositions?)?|usps?|value\s+proposition|competitive\s+advantage|'
        r'strawman\s+competitor|commercial\s+benchmark|incumbent(\s+technology)?|how\s+to\s+write\s+(a\s+)?usp|'
        r'differentiate\s+my\s+proposal|competitive\s+edge)\b',
        lower
    ))

    is_ansoff_coach = bool(re.search(
        r'\b(ansoff(\s+matrix)?|market\s+penetration|product\s+development|market\s+development|diversification|'
        r'which\s+ansoff\s+quadrant|ansoff\s+quadrants?|market\s+strategy)\b',
        lower
    ))

    # NEW: Table 2 (Expected Results & Publication-Format Table) & Consistency Matrix Coach
    is_results_table_coach = bool(re.search(
        r'\b(table\s*2|expected\s+results\s+table|acceptance\s+criteria(\s+table)?|'
        r'how\s+to\s+format\s+table\s*2|results\s+table(\s+format)?|show\s+results\s+in\s+a\s+table|'
        r'formulate\s+(a\s+)?table|add\s+(the\s+)?rows\s+and\s+columns|add\s+columns?\s+to\s+table|'
        r'why\s+did\s+you\s+put\s+the\s+5\.2\s+table|why\s+(is\s+)?(the\s+)?5\.2\s+table|'
        r'aim\s+of\s+(the\s+)?(table\s*2|5\.2\s+table)|purpose\s+of\s+table\s*2|'
        r'acceptance\s+criterion)\b',
        lower
    ))

    is_consistency_matrix_coach = bool(re.search(
        r'\b(scientific\s+consistency|consistency\s+matrix|aim\s*→\s*method|method\s*→\s*outcome|'
        r'logic\s+mismatch|cross(-|\s+)section\s+alignment|align\s+objectives\s+and\s+methods|'
        r'traceability\s+matrix)\b',
        lower
    ))

    # NEW: Title Formulation & Evaluation Intent (Criterion 1)
    is_title_coach = bool(re.search(
        r'\b(title|project name|name my project)\b',
        lower
    )) and (
        bool(re.search(r'\b(how\s+is|evaluate|rate|critique|check|review|feedback|good|ok|improve|formulate|structure|blueprint|formula|recommend|suggest|what do you think|problem|what\s+should\s+i\s+do|how\s+to\s+fix|fix)\b', lower))
        or clean_trim in ["title", "my title", "project title", "title review", "title check", "how is my title", "how is my title?", "what is the problem in the title", "what do you think about the title"]
        or bool(re.search(r'\b(how\s+is|what\s+is\s+the\s+problem\s+in|what\s+do\s+you\s+think\s+(about|of)|what\s+should\s+i\s+do\s+with)\s+(my|the|this)\s+title\b', lower))
    )

    # NEW: Specific Aims Formulation & Audit Intent (Chapter 9 & 22)
    is_aims_coach = (bool(re.search(
        r'\b(aim|aims|specific\s+aims?|objective|objectives|section\s*3)\b',
        lower
    )) and (
        bool(re.search(r'\b(how|write|draft|formula|decouple|structure|guide|what\s+do\s+you\s+think|think|review|check|evaluate|rate|critique|audit|feedback|how\s+are|how\s+is|good|ok|improve|look|status|problem|missing|fix|suggestion)\b', lower))
        or clean_trim in ["aims", "objectives", "specific aims", "my aims", "my objectives", "what do you think about the objectives", "what do you think of the objectives"]
        or bool(re.search(r'\b(what\s+do\s+you\s+think\s+(about|of)|how\s+are|review|check|evaluate|audit|critique)\s+(the|my|our|these)?\s*(specific\s+)?(objectives?|aims?)\b', lower))
    ))

    # NEW: Methodology & Experimental Design Audit Intent (Chapter 9 & 23)
    is_methodology_coach = (bool(re.search(
        r'\b(method|methods|methodology|protocol|protocols|section\s*4)\b',
        lower
    )) and (
        bool(re.search(r'\b(how|write|draft|structure|guide|what\s+do\s+you\s+think|think|review|check|evaluate|rate|critique|audit|feedback|how\s+is|how\s+are|good|ok|improve|look|status|missing|fix|controls?)\b', lower))
        or clean_trim in ["methodology", "methods", "my methods", "my methodology", "what do you think about the methodology"]
        or bool(re.search(r'\b(what\s+do\s+you\s+think\s+(about|of)|how\s+is|review|check|evaluate|audit|critique)\s+(the|my|our)?\s*(methodology|methods?|protocols?)\b', lower))
    ))

    # NEW: Grant Budgeting in EGP Intent (Chapter 25)
    is_budget_coach = bool(re.search(
        r'\b(budget|egp|egyptian\s+pounds?|how\s+to\s+write\s+(a\s+)?budget|budget\s+justification|'
        r'itemized\s+budget|reagents?\s+cost|equipment\s+cost|indirect\s+costs?|direct\s+costs?|'
        r'contingency\s+fund|budget\s+categories|grant\s+budget)\b',
        lower
    ))

    # NEW: Timeline & Gantt Chart Intent (Chapter 24)
    is_timeline_coach = bool(re.search(
        r'\b(gantt(\s+chart)?|timeline|milestones?|quarterly\s+milestone|project\s+schedule|'
        r'timeline\s+template|contingency\s+plan|plan\s+b|risk\s+management)\b',
        lower
    ))

    # NEW: Experimental Controls Intent (Chapter 23)
    is_controls_coach = bool(re.search(
        r'\b(what\s+controls\s+do\s+i\s+need|experimental\s+controls?|negative\s+control|'
        r'positive\s+control|vehicle\s+control|sham\s+control|matrix(-|\s+)matched|blank\s+sample|'
        r'assay\s+controls?)\b',
        lower
    ))

    # NEW: Statistical Rigor & Limit of Detection Intent (Chapter 2 & 23)
    is_stats_coach = bool(re.search(
        r'\b(statistical\s+design|statistical\s+analysis|statistics|p-value|sample\s+size|power\s+calculation|'
        r'(anova|t-test)\b.*\b(anova|t-test)|choose\s+between\s+t-test|limit\s+of\s+detection|'
        r'how\s+to\s+calculate\s+lod|probit\s+regression|lod\s+formula)\b',
        lower
    ))

    # NEW: APA 7th Edition Citation & Reference List Coaching Intent (Chapter 5)
    is_citation_coach = bool(re.search(
        r'\b(apa\s*7(th)?|apa\s+style|apa\s+citation|apa\s+format|how\s+to\s+cite|'
        r'in-text\s+citation|in\s+text\s+citation|parenthetical\s+citation|narrative\s+citation|'
        r'reference\s+list|reference\s+format|how\s+to\s+reference|how\s+many\s+authors|'
        r'et\s+al\b|et\s+al\.|hanging\s+indent|sentence\s+case\s+for\s+title|how\s+to\s+cite\s+a\s+(journal|book|preprint|website|thesis|dissertation|conference|dataset|software|patent)|'
        r'cite\s+biorxiv|cite\s+arxiv|cite\s+a\s+paper|doi\s+format|doi\s+link|retrieved\s+from|'
        r'zotero|mendeley|reference\s+manager|vancouver\s+(vs|style)|common\s+apa\s+mistakes|'
        r'citation\s+rules?|referencing\s+rules?)\b',
        lower
    )) or (bool(re.search(r'\b(cite|citing|citation|citations|reference|references|bibliography)\b', lower)) and bool(re.search(r'\b(how|rule|rules|format|guide|style|correct|check|audit|apa|mistake|template)\b', lower)))

    # NEW: Reviewer 2 Mock Viva Defense ("Grill Me") Intent
    is_grilling = bool(re.search(
        r'\b(grill\s+me|reviewer\s+2|mock\s+defense|mock\s+viva|simulate\s+oral\s+defense|cross(-|\s+)examin|defense\s+mode)\b',
        lower
    ))

    # NEW: Glossary & Scientific Definition Lookup
    glossary_match = get_glossary_term(text) if get_glossary_term else None
    is_glossary = bool(glossary_match) and bool(re.search(
        r'\b(what\s+is|what\s+are|define|definition|explain|meaning\s+of|what\s+does.*mean|tell\s+me\s+about|how\s+to\s+calculate|formula\s+for)\b',
        lower
    ) or clean_trim == (glossary_match.get("term", "").lower() if glossary_match else "")) and not (is_results_table_coach or is_consistency_matrix_coach)

    is_gap_coach = bool(re.search(
        r'\b(how\s+to\s+write\s+(a\s+)?(literature\s+)?gap|gap\s+sentence|gap\s+pivot|'
        r'formulate\s+(a\s+)?gap|finding\s+the\s+gap|literature\s+gap\s+statement)\b',
        lower
    ))

    is_guide_direct = bool(re.search(
        r'\b(bt301\s+guide|course\s+guide|complete\s+guide|student\s+guide|'
        r'pre-submission\s+checklist|master\s+checklist|grading\s+rubric|how\s+is\s+my\s+proposal\s+graded|'
        r'how\s+will\s+it\s+be\s+graded|stuck\s+finder|quick\s+finder|fill-in\s+templates?)\b',
        lower
    )) or bool(re.match(r'^(show|open|read|view)?\s*chapter\s*(\d+)', lower))

    # Comprehensive Contextual Guidance & Co-Thinking Intent
    is_guidance_request = (bool(re.search(
        r'\b(help\s+me\s+do\s+this|help\s+me\s+with\s+this|guide\s+me\s+on\s+this|guide\s+me\s+through\s+this|'
        r'can\s+you\s+guide\s+me|can\s+you\s+help\s+me|how\s+do\s+i\s+do\s+this|what\s+should\s+i\s+do|'
        r'what\s+should\s+i\s+write|where\s+do\s+i\s+start|how\s+to\s+start|help\s+me\s+with\s+my\s+project|'
        r'what\s+is\s+next|next\s+step|suggest\s+next\s+step|tell\s+me\s+what\s+to\s+do|walk\s+me\s+through|'
        r'guide\s+me\s+to\s+write|help\s+me\s+to\s+write|help\s+me\s+write)\b',
        lower
    )) or (clean_trim in ["help me", "guide me", "help me please", "guide me please", "what should i do next", "how do i do this", "help", "guide"])) and not is_sentence_coach and not is_hypothesis_coach and not is_gap_coach and not is_citation_coach

    # Daily human conversation intents
    is_weather = bool(re.search(r'\b(weather|rain|raining|sunny|clouds?|cloudy|forecast|hot outside|cold outside|temperature outside)\b', lower))
    is_how_are_you = bool(re.match(r'^(how are you|how are you doing|hows it going|how is it going|how are things|hows your day|how do you feel|whats up|sup|doing good)\??$', clean_trim)) or bool(re.search(r'\b(how are you doing|how have you been|how are things with you)\b', lower))
    is_fatigue = bool(re.search(r'\b(tired|exhausted|need a break|taking a break|coffee|lunch|dinner|sleepy|sleep|hungry)\b', lower)) and not bool(re.search(r'\b(cell|gene|expression|protein|assay|aim|proposal)\b', lower))
    is_food = bool(re.search(r'\b(what should i eat|what to eat|food|lunch|dinner|breakfast|snack|hungry|recipe|cook|cooking|meal|diet|nutrition|boba)\b', lower)) and not bool(re.search(r'\b(cell|gene|expression|protein|assay|aim|proposal)\b', lower))
    is_wellness = bool(re.search(r'\b(sleep|sleepy|insomnia|wake up|stress|stressed|anxious|anxiety|relax|calm down|overwhelmed|headache|burnout)\b', lower)) and not bool(re.search(r'\b(cell|gene|expression|protein|assay|aim|proposal)\b', lower))
    is_entertainment = bool(re.search(r'\b(recommend\b.*\b(movie|film|show|series|music|song|book|game|podcast)|'
                                       r'what movie|what show|what song|what book|suggest\b.*\b(movie|film|show|book|song|music))\b', lower)) and not bool(re.search(r'\b(cell|gene|expression|protein|assay|aim|proposal)\b', lower))
    is_motivation = bool(re.search(r'\b(motivate me|procrastinat|feeling down|cheer me up|bored|need advice|give me advice|tell me something interesting)\b', lower)) and not bool(re.search(r'\b(cell|gene|expression|protein|assay|aim|proposal)\b', lower))
    is_joke = bool(re.search(r'\b(tell me a joke|say something funny|make me laugh|joke|humor)\b', lower))
    is_ai_q = bool(re.search(r'\b(are you (a |an )?(real|human|real human|ai|robot|bot|person)|are you real|are you human|are you an ai|are you a robot|do you sleep|do you have feelings|what do you think about humans|who created you|who made you|who programmed you|what are you|who are you)\b', lower))
    is_greeting = bool(re.match(r'^(hello|hi|hey|good\s*(morning|afternoon|evening)|greetings|yo|sup|hola)\b', clean_trim))
    is_gratitude = bool(re.match(r'^(thanks|thank\s*you|thx|much\s*appreciated|appreciate\s*it)\b', clean_trim))

    # -------------------------------------------------------------------------
    # BT_301 PEDAGOGICAL INTEGRITY & SOCRATIC ACADEMIC MENTOR INTERCEPTOR
    # Strictly enforces: Scaffold, Don't Solve — Never Ghostwrite for Students
    # -------------------------------------------------------------------------
    is_educational_inquiry = bool(re.search(
        r'\b(how\s+to\s+(write|formulate|structure|draft|develop|design|decouple)|explain|teach|what\s+is|what\s+are|guidelines?\s+for|difference\s+between)\b',
        lower
    ))

    is_ghostwriting_intent = not is_educational_inquiry and bool(re.search(
        r'\b(write|draft)\s+(me\s+)?(\d+\s+|a\s+|an\s+|my\s+|the\s+)?(complete\s+|specific\s+)?(proposal|introduction|background|abstract|methodology|methods|aims?|objectives?|hypothes[ie]s|literature\s+review|results?|discussion|conclusion|paper)\b|'
        r'\b(write|draft)\s+.*?\b(for\s+me)\b|'
        r'\bgenerate\s+(\d+\s+|a\s+|an\s+|my\s+|the\s+)?(complete\s+)?(proposal|introduction|background|abstract|methodology|methods|aims?|objectives?|hypothes[ie]s|paper|section|blueprint)\b|'
        r'\bgive\s+me\s+(\d+\s+|a\s+|an\s+|my\s+|some\s+)?(specific\s+)?(title|aims?|objectives?|hypothes[ie]s|introduction|methodology|methods|proposal|paragraph|section|ready(-|\s+)to(-|\s+)submit)\b|'
        r'\bfix\s+my\s+(methodology|introduction|aims?|objectives?|hypothes[ie]s|proposal|draft|methods)\s*(for\s+me)?\b|'
        r'\brewrite\s+(this|my)\s+(section|draft|introduction|methodology|proposal|abstract|text|paragraph|methods)\b|'
        r'\b(do\s+this|write\s+this|finish\s+this)\s+for\s+me\b|'
        r'\bauto(-|\s+)assemble\s+(my\s+|the\s+)?(proposal|blueprint|complete\s+proposal)\b|'
        r'\bmake\s+(me\s+)?a\s+(proposal|draft|title|aim)\b',
        lower
    ))

    if is_ghostwriting_intent:
        thinking_steps.append("Pedagogical Firewall Triggered: Detected request to ghostwrite proposal content.")
        thinking_steps.append("Enforcing Academic Integrity: AI functions strictly as mentor and reviewer, never proposal writer.")
        
        # Identify targeted component
        if any(k in lower for k in ["intro", "background", "literature review"]):
            comp = "introduction"
        elif any(k in lower for k in ["aim", "objective"]):
            comp = "aims"
        elif any(k in lower for k in ["method", "protocol"]):
            comp = "methodology"
        elif any(k in lower for k in ["abstract"]):
            comp = "abstract"
        elif any(k in lower for k in ["title"]):
            comp = "title"
        elif any(k in lower for k in ["hypothes"]):
            comp = "hypothesis"
        elif any(k in lower for k in ["usp", "unique selling", "value proposition", "strawman", "competitive advantage"]):
            comp = "usp"
        else:
            comp = "proposal_blueprint" 

        # Preserve Research Identity & Active Context
        project_label = live_title or "your biotechnology proposal"
        chassis_label = live_chassis or "your biological system/model"
        tool_label = live_tool or "your active intervention/tool"
        target_label = live_target or "your measurable target"

        combined_context = f"{live_title} {live_chassis} {live_tool} {live_target}".lower()
        is_phyto_cream = bool(re.search(r'\b(plant|calendula|herb|herbal|extract|cream|topical|ointment|gel|emulsion|skin|wound|curcumin|flavonoid|faradiol|erythema|dermatitis)\b', combined_context))
        is_comp = bool(re.search(r'\b(docking|in silico|virtual screen|binding affinity|rmsd|alphafold|autodock)\b', combined_context))
        is_amr = bool(re.search(r'\b(amr|antimicrobial|antibacterial|mic\b|mbc|colistin|mcr-?1)\b', combined_context))

        thinking_steps.append(f"Preserving student research identity for: '{project_label}'.")
        thinking_steps.append(f"Tailoring Socratic scaffolding to component: {comp.upper()}.")

        if comp == "introduction":
            if is_phyto_cream:
                specific_q = f"For *'{project_label}'*, what is the published clinical or technical drawback of current conventional standard treatments (e.g. skin thinning from recurrent topical corticosteroids), and how will standardizing {tool_label} directly address that limitation?"
            elif is_comp:
                specific_q = f"For *'{project_label}'*, what is the computational bottleneck in current screening models that your study addresses, and what experimental validation data will you benchmark against?"
            elif is_amr:
                specific_q = f"For *'{project_label}'*, what is the quantified epidemiological prevalence of resistance against current frontline antibiotics that establishes the urgency of your study?"
            else:
                specific_q = f"For *'{project_label}'*, what specific clinical or biophysical limitation of current conventional technology creates the knowledge gap your study will address?"

            reply = f"""🎓 **Academic Mentor Guidance — Developing Your Introduction (Section 2.1)**

⚠️ **Academic Integrity Notice:** As your academic research mentor, I do not write proposal text, introductions, or paragraphs for you. Submitting AI-generated prose violates university academic integrity standards (AI ceiling ≤25%), deprives you of intellectual ownership, and leaves you vulnerable during your faculty viva defense.

Instead, let us build a publication-grade introduction using the **4-Tier Inverted Funnel**:

---

### 1. 📐 Inverted Funnel Architecture (Revision Criteria):
• **Tier 1 (Global Burden):** Quantify real-world impact (e.g. population affected, economic loss).
• **Tier 2 (Current Standard & Limit):** State standard therapy and its adverse effect or delivery barrier.
• **Tier 3 (Literature Gap):** State the exact technical bottleneck unsolved in published literature.
• **Tier 4 (Your Proposed Project):** State how your active intervention directly solves that bottleneck.

---

### 2. ✍️ Fill-in-the-Blank Sentence Blueprints (Bracket Scaffolds):
• *Tier 1:* "[Condition] affects [quantified burden, e.g. 15% of patients], causing [clinical consequence]."
• *Tier 2:* "Standard therapy with [comparator] is constrained by [adverse effect/cost]."
• *Tier 3:* "Current formulations fail to resolve [gap], leaving [pathway] unaddressed."
• *Tier 4:* "This proposal evaluates [tool] in [chassis] to achieve [target milestone]."

---

### 3. 💡 Guiding Socratic Questions to Draft Your Introduction:
1. {specific_q}
2. Which 2 peer-reviewed papers will you cite to support your problem burden and standard comparator?

---

### 4. ✅ Self-Check Checklist:
⬜ Did you lead with broad burden before narrowing?  
⬜ Did you cite an established standard reference or clinical comparator?  
⬜ Did you replace vague phrases with formal biomedical terminology?  
⬜ Did you avoid saying 'not enough studies have been done'?

👉 **Next Step:** Fill the bracket slots with your project data in Section 2, or paste your draft here for Socratic critique!"""

            actions = [
                {"label": "Jump to Section 2 in Editor", "icon": "✏️", "onClickJs": "jumpToEditorSection('section-2-1-unified')"},
                {"label": "Review Inverted Funnel Rules", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(9);"}
            ]
            suggestions = [
                {"text": "💡 How do I introduce the literature gap?", "prompt": "how to write a literature gap statement"},
                {"text": "📊 What quantitative numbers should I cite in Tier 1?", "prompt": "how to find epidemiological statistics for my background"}
            ]

        elif comp == "aims":
            if is_phyto_cream:
                q1 = f"For *'{project_label}'*, what is the first tangible material or standardized extract parameter you must prepare and analytically verify (e.g. HPLC quantification of active markers) in Aim 1?"
                q2 = "What quantitative biological assay (e.g. LPS-stimulated macrophage suppression of TNF-α/IL-6) and clinical comparator control (e.g. hydrocortisone 1%) will define your Aim 2 endpoint?"
            elif is_amr:
                q1 = f"For *'{project_label}'*, what specific strain and standard MIC microdilution threshold defines your primary Aim 1 milestone?"
                q2 = "How will you decouple downstream synergy or resistance-prevention testing in Aim 2 so progress is not halted if Aim 1 optimization takes longer?"
            else:
                q1 = f"For *'{project_label}'*, what is the very first physical construct, extract, or computational dataset you must assemble and validate in Aim 1?"
                q2 = "What quantitative endpoint and benchmark comparator will you measure in Aim 2 to prove that your tool works?"

            reply = f"""🎯 **Academic Mentor Guidance — Formulating Decoupled Specific Aims (Section 3)**

⚠️ **Academic Integrity Notice:** As your academic research mentor, I cannot write ready-to-submit specific aims for you. Formulating experimental milestones is the core intellectual work of a biotechnology researcher.

Here is how we build 3 decoupled specific aims for your project:

---

### 1. 📐 Specific Aims Architecture Criteria (BT301 Rubric Criterion 3):
• **Aim 1 (Preparation / Standardization):** Produce, extract, clone, synthesize, or standardize your active intervention with analytical quality control.
• **Aim 2 (Efficacy & Primary Bioassay):** Evaluate performance in an authentic biological model benchmarked head-to-head against an established reference standard.
• **Aim 3 (Mechanism, Safety or Delivery Kinetics):** Characterize underlying mechanism, permeation/release kinetics, or safety margin.

---

### 2. ✍️ Fill-in-the-Blank Specific Aims Blueprints:
• **Aim 1 (Preparation):** "To [isolate/synthesize/clone] [active tool] from [source] and quantify [marker compound] to achieve [≥X% purity/yield] via [analytical method]."
• **Aim 2 (Efficacy):** "To evaluate [tool] in [cell line/strain/model] benchmarked against [positive comparator] to achieve [target milestone, e.g. IC50 ≤ X μg/mL]."
• **Aim 3 (Mechanism/Safety):** "To determine [permeation/mechanism/safety margin] across [system] relative to [vehicle control baseline]."

---

### 3. 🛡️ The Non-Negotiable Aim Decoupling Rule:
Downstream aims must NOT suffer from **Domino Collapse**. If Aim 1 yields low expression, Aim 2 must have an active parallel fallback (e.g. commercially sourced standard).

---

### 4. 💡 Guiding Socratic Questions for Your Project:
1. {q1}
2. {q2}
3. Which measurable action verbs (*Quantify, Formulate, Validate, Optimize*) will lead each aim?

---

### 5. ✅ Self-Check Checklist:
⬜ Does each aim start with an active scientific verb (*Formulate, Quantify, Validate*)?  
⬜ Did you avoid passive verbs like *'Study'*, *'Investigate'*, or *'Look into'*?  
⬜ Is each aim linked to an explicit quantitative endpoint and benchmark comparator?

👉 **Next Step:** Draft your 3 milestones in Section 3 of the editor, and click 'Check My Reasoning' to evaluate their decoupling!"""

            actions = [
                {"label": "Jump to Section 3 in Editor", "icon": "🎯", "onClickJs": "jumpToEditorSection('section-3-1-aim')"},
                {"label": "Open Chapter 22: Specific Aims Guide", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(22);"}
            ]
            suggestions = [
                {"text": "🛡️ How to decouple Aim 2 from Aim 1?", "prompt": "how to decouple Aim 2 from Aim 1?"},
                {"text": "✍️ What action verbs are approved for Aims?", "prompt": "approved action verbs for specific aims"}
            ]

        elif comp == "methodology":
            if is_phyto_cream:
                ctrl_q = "What negative vehicle control (e.g. blank cream base without extract) and positive clinical comparator (e.g. hydrocortisone 1% cream) will you test side-by-side to prove that excipients do not cause false-positive effects?"
                assay_q = "How do you distinguish between genuine anti-inflammatory efficacy and extract-induced cytotoxicity in your macrophage assays (e.g. MTT/LDH viability testing, Selectivity Index ≥ 3.0)?"
            elif is_comp:
                ctrl_q = "What co-crystallized native ligand redocking benchmark (RMSD < 2.0 Å) and known active vs. decoy datasets will validate your virtual screening protocol?"
                assay_q = "What wet-lab biophysical binding assay (e.g. SPR, ITC, or enzyme inhibition IC50) will validate your top computational candidate hits?"
            elif is_amr:
                ctrl_q = "What ATCC reference quality-control strain and standard antibiotic control will validate your broth microdilution plate readings under CLSI M07 standards?"
                assay_q = "How will you standardize your inoculum density (0.5 McFarland standard) and determine whether the mechanism is bactericidal or bacteriostatic (MBC vs MIC)?"
            else:
                ctrl_q = "What negative vehicle/mock control and positive reference standard will you run in parallel to benchmark performance?"
                assay_q = "What exact analytical instrumentation, operating conditions, and replicate power (n = 3, ANOVA) will you declare?"

            reply = f"""🧪 **Academic Mentor Guidance — Structuring Your Experimental Methodology (Section 4)**

⚠️ **Academic Integrity Notice:** As your academic mentor, I review and diagnose experimental protocols, but I do not write or rewrite methodology on your behalf. Grant reviewers assess your ability to design controlled, reproducible scientific experiments.

Here is the standard framework to structure your experimental methodology:

---

### 1. 📐 Methodology Evaluation Criteria:
• **Logical Experimental Design:** Ensure your study design logically connects: Research Question → Objectives → Variables/Outcomes → Study Design & Methods → Paired Controls → Measurements → Statistical Analysis.
• **Paired Scientific Controls:** Every biological assay requires both a **negative vehicle control** (blank matrix, untreated cells) and an **established positive reference standard**.
• **Statistical Power & Replicates:** Declare biological triplicates (n = 3), independent experimental batches, and formal hypothesis testing (e.g. one-way ANOVA with post-hoc test, p < 0.05).
• **Proposal Tense:** Write procedures in formal future tense (*'will be incubated'*, *'will be quantified'*).

---

### 2. ✍️ Fill-in-the-Blank Methodology Blueprints:
• **Phase 1 (Preparation):** "[Source] will be prepared under [conditions] and quantified for [purity] via [instrumentation]."
• **Phase 2 (Controlled Testing):** "[Model] will be treated with [concentrations] alongside vehicle control [blank base] and positive control [comparator] in triplicates (n = 3)."
• **Phase 3 (Statistical Readout):** "Data will be analyzed using [one-way ANOVA, p < 0.05], defining success as [≥X% change] without cytotoxicity."

---

### 3. 💡 Guiding Socratic Questions for Your Project:
1. {ctrl_q}
2. {assay_q}

---

### 4. ✅ Self-Check Checklist:
⬜ Are all procedures structured into sequential experimental phases?  
⬜ Are negative vehicle baselines and positive comparators explicitly named?  
⬜ Are analytical conditions declared (temperatures, concentrations, wavelengths, columns)?  
⬜ Are procedures written in formal future tense?

👉 **Next Step:** Update your methodology in Section 4 of the editor, then submit your draft for Socratic review!"""

            actions = [
                {"label": "Jump to Section 4 in Editor", "icon": "🧪", "onClickJs": "jumpToEditorSection('section-4-1-methodology')"},
                {"label": "Check My Controls & Statistics", "icon": "🔍", "onClickJs": "quickSendCopilotPrompt('what controls do i need for my proposal')"}
            ]
            suggestions = [
                {"text": "🔬 What controls do I need?", "prompt": "what controls do i need for my proposal"},
                {"text": "📊 How to format biological replicates and statistics?", "prompt": "statistical design and replicates for my methodology"}
            ]

        elif comp == "title":
            reply = f"""🏷️ **Academic Mentor Guidance — Formulating Your Research Title (Step 1)**

⚠️ **Academic Integrity Notice:** As your academic mentor, I do not generate ready-to-submit titles for you. Your title must accurately represent your own experimental scope and biological model.

---

### 1. 📐 The 4-Piece Publication Title Formula:
Assemble your title using this active, publication-grade formula:
**Title Blueprint:** [Active Tool / Extract] in [Delivery Matrix] tested in [Biological Chassis] to [Target Benchmark] for [Problem / Application]

• **Publication Standard (Delivery Vehicle vs. Biological Model):** Remember that a formulation like *'Cream'* or *'Gel'* is the delivery vehicle, not the biological chassis. Peer-reviewed papers declare their testing model (*in vitro* cell line like RAW 264.7 macrophages, *ex vivo* porcine skin Franz cells, or *in vivo* BALB/c mice) and lead directly with active formulation and evaluation!

---

### 2. ✍️ Fill-in-the-Blank Title Blueprint:
• **Template:** "[Active Tool] in [Delivery Matrix] for [Mechanistic Action] in [Biological Chassis] to Mitigate [Target Problem]"  
• *Domain Example:* "Standardized Calendula officinalis Emulsion for Downregulation of TNF-alpha in RAW 264.7 Macrophages to Mitigate Corticosteroid-Resistant Dermatitis"

---

### 3. 💡 Guiding Socratic Questions to Formulate Your Title:
1. What is the active substance, molecular tool, or formulation you are developing ({tool_label})?
2. In what biological system, cell model, or delivery chassis ({chassis_label})?
3. What measurable target number or benchmark defines success ({target_label})?
4. What clinical, agricultural, or environmental problem does it solve?

👉 **Next Step:** Combine your answers to the 4 questions above and enter your title in Step 1 of the editor!"""

            actions = [
                {"label": "Jump to Title Input in Editor", "icon": "✏️", "onClickJs": "jumpToEditorSection('proposal-title-input')"},
                {"label": "Review 3 Strategic Pillars", "icon": "🏷️", "onClickJs": "jumpToEditorSection('pillar-chassis')"}
            ]
            suggestions = [
                {"text": "💡 How do I avoid passive phrasing in titles?", "prompt": "how to write a good biotechnology proposal title"},
                {"text": "🎯 How do I define my target milestone?", "prompt": "how to define a measurable target milestone in my proposal"}
            ]

        elif comp == "abstract":
            reply = f"""📋 **Academic Mentor Guidance — Crafting Your Executive Abstract (Section 1)**

⚠️ **Academic Integrity Notice:** As your academic mentor, I do not write abstracts for students. An abstract must reflect your own synthesized summary of your proposed investigation.

---

### 1. 📐 Executive Abstract Criteria (BT301 Rubric Criterion 2):
• **Strict Word Count:** Must remain strictly between **150 and 250 words**. Under 150 words is penalized as incomplete; over 250 words is disqualified by grant review systems.
• **4-Component Structure:**
  1. *Problem Burden (1–2 sentences):* Quantified real-world significance and clinical/environmental burden.
  2. *Current Limitation & Gap (1–2 sentences):* Where existing standard methods fail.
  3. *Proposed Tool & Methodology (2–3 sentences):* Your active intervention, model system, and paired controls.
  4. *Expected Milestone (1 sentence):* Primary quantitative deliverable benchmarked against standard controls.

---

### 2. ✍️ Fill-in-the-Blank Abstract Blueprint (150–250 words):
• *Burden:* "[Condition] affects [quantified prevalence], resulting in [consequence]."
• *Current Limitation:* "Current standard treatment using [comparator] is limited by [drawback]."
• *Proposed Tool & Chassis:* "Here, we propose [active tool] formulated in [delivery system] evaluated in [model chassis]."
• *Controls & Endpoint:* "Using negative vehicle controls and [positive comparator] in triplicates (n = 3), we target [quantitative milestone]."

---

### 3. 💡 Guiding Socratic Questions:
1. What is the primary quantified problem metric you are addressing?
2. What specific biological readout will prove your intervention's efficacy?

👉 **Next Step:** Draft your abstract in Section 1 of the editor, and click 'Check My Reasoning' to verify word count and compliance!"""

            actions = [
                {"label": "Jump to Section 1 in Editor", "icon": "📋", "onClickJs": "jumpToEditorSection('proposal-abstract-input')"},
                {"label": "Check Abstract Rubric Checklist", "icon": "🔍", "onClickJs": "quickSendCopilotPrompt('how will my proposal be graded')"}
            ]
            suggestions = [
                {"text": "📏 Check abstract word count", "prompt": "how is abstract word count graded in BT301"},
                {"text": "🌟 What makes an abstract grant-ready?", "prompt": "what makes an abstract grant ready"}
            ]

        elif comp == "usp":
            reply = f"""⭐ **Academic Mentor Guidance — Formulating Your Unique Selling Proposition (USP)**

⚠️ **Academic Integrity Notice:** As your academic research mentor, I do not invent commercial claims or generate market positioning on your behalf. Grant reviewers scrutinize your ability to identify the concrete technical and mechanistic differentiation of your proposed bio-innovation.

Here is how we construct a winning biotechnology USP before filling the Ansoff Matrix:

---

### 1. 📐 The 3-Part Winning Biotechnology USP Formula:
Never use the 'Strawman Competitor' trap (*"unlike traditional methods"* or *"unlike conventional approaches"*). Name the exact commercial or published benchmark!

**USP Template:**
*"Unlike **[Named Gold Standard / Commercial Incumbent]**, our **[Bio-Engineered Tool / Formulation]** **[Specific Mechanistic / Technical Superiority]**, achieving **[Quantifiable Performance Metric]** and providing **[Concrete Stakeholder / Clinical Benefit]**."*

• *Example (Phytochemical / Topical):* "Unlike conventional 1% hydrocortisone cream which causes skin thinning upon recurrent use, our standardized *Calendula officinalis* emulsion selectively suppresses TNF-α and NO by >65% without inducing epidermal cytotoxicity."
• *Example (Recombinant Enzyme / White Biotech):* "Unlike commercial *Aspergillus niger* esterase which denatures rapidly above 55 °C, our engineered *Bacillus* E1 esterase retains >50% catalytic viability after 48 h at 60 °C, cutting industrial enzyme replenishment costs."

---

### 2. 💡 Guiding Socratic Questions to Formulate Your USP:
1. What exact commercial benchmark or published method is currently the gold standard in your field?
2. What specific biophysical or chemical failure mode of that standard does {tool_label} directly solve?
3. What quantitative metric (e.g. % yield, IC50, thermal half-life, detection limit) proves your tool's superiority?
4. Who is the tangible clinical, environmental, or manufacturing beneficiary?

---

### 3. ✅ Self-Check Checklist:
⬜ Did you name the exact commercial standard rather than saying 'traditional methods'?  
⬜ Is the superiority mechanistic (e.g. kinetic stability, receptor affinity) rather than marketing hype?  
⬜ Is there a quantified target metric?  
⬜ Does your USP directly align with your Ansoff quadrant (Market Penetration vs. Product Development)?

👉 **Next Step:** Fill the bracket slots with your project data in the USP card of Step 1, or share your draft here for Socratic feedback!"""

            actions = [
                {"label": "Jump to USP Card in Editor", "icon": "⭐", "onClickJs": "jumpToEditorSection('card-section-usp')"},
                {"label": "Review Ansoff Matrix", "icon": "📊", "onClickJs": "jumpToEditorSection('card-section-ansoff')"}
            ]
            suggestions = [
                {"text": "💡 How to avoid the strawman competitor trap?", "prompt": "how to avoid strawman competitor in my biotechnology proposal"},
                {"text": "📊 How does my USP connect to the Ansoff Matrix?", "prompt": "how to choose between Market Penetration and Product Development in Ansoff"}
            ]

        else: # proposal_blueprint or general ghostwrite request
            reply = f"""🧭 **Academic Mentor Guidance — Proposal Architecture & Socratic Roadmap**

⚠️ **Academic Integrity Notice:** In BT_301, proposals must be independently conceived, designed, and authored by the student investigator. Automatic proposal generators create superficial drafts that immediately collapse during oral faculty cross-examination.

Here is your step-by-step roadmap to build your proposal independently:

| Step | Component | Core Academic Standard |
| :--- | :--- | :--- |
| **1** | **Title & 3 Pillars** | Lead with active tool/intervention; specify biological system and measurable target. Avoid *'Study of...'*. |
| **2** | **Inverted Funnel** | Move deductively from global problem burden to current standard, literature gap, and your intervention. |
| **3** | **Decoupled Aims** | Structure 3 milestones with parallel reference controls to avoid domino failure. |
| **4** | **5-Phase Methods** | Declare vehicle negative control, positive comparator, analytical parameters, and n = 3 statistics. |
| **5** | **Technical Benchmarks** | Establish quantitative thresholds and milestone acceptance criteria for every work package. |

---

### ✍️ Fill-in-the-Blank Section Starter Blueprints:
• **Step 1 (Title):** "[Tool] in [Matrix] to [Target Action] in [Model Chassis] for [Application]"
• **Step 2 (Introduction):** "[Condition] affects [Burden], but standard [Comparator] is limited by [Deficiency]."
• **Step 3 (Aims):** "Aim 1: [Standardize Tool] | Aim 2: [Validate in Chassis vs Comparator] | Aim 3: [Safety/Mechanism]"
• **Step 4 (Methods):** "Evaluate [Tool] in [Chassis] with [Vehicle Control] and [Comparator] (n = 3, p < 0.05)."
• **Step 5 (Benchmarks):** "Milestone threshold: Target yield >= 85% with CV < 5% across 3 biological replicates."

---

### 💡 Where should we begin?
Tell me which specific section of *'{project_label}'* you would like to work on first, and I will coach you through formulating your own draft!"""

            actions = [
                {"label": "Review Section 1 Title & Pillars", "icon": "🏷️", "onClickJs": "jumpToEditorSection('proposal-title-input')"},
                {"label": "Review Section 2 Introduction", "icon": "📖", "onClickJs": "jumpToEditorSection('section-2-1-unified')"},
                {"label": "Review Section 3 Aims", "icon": "🎯", "onClickJs": "jumpToEditorSection('section-3-1-aim')"},
                {"label": "Simulate Faculty Viva Defense", "icon": "🎙️", "onClickJs": "quickSendCopilotPrompt('grill me on this proposal')"}
            ]
            suggestions = [
                {"text": "🎯 Let's review my Specific Aims", "prompt": "how to write decoupled specific aims"},
                {"text": "🧪 What controls do I need in Section 4?", "prompt": "what controls do i need for my proposal"}
            ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "academic_mentor_guidance"
        }

    # PAPER DECODER (ANALYST MODE): Grant Evaluator & Evidence Deconstruction
    if is_paper_decoder and decode_paper_analyst:
        thinking_steps.append("Detected Paper Decoder request (Grant Evaluator & Scientific Analyst Mode).")
        thinking_steps.append("Deconstructing paper strictly adhering to core evidence rules: evidence only, numbers first, no hype, stated vs unstated limitations, and 6-part analyst structure.")

        paper_raw = paper_prefix_match.group(1).strip() if paper_prefix_match else re.sub(
            r'^(?:please\s+)?(?:decode|analyze|deconstruct|run\s+paper\s+decoder\s+on)\s+(?:this\s+)?(?:paper)?[:\s]*',
            '', text, flags=re.I
        ).strip()

        # Proposal context
        p_context = (
            active_proposal_context.get("title", "") or
            active_proposal_context.get("target", "") or ""
        )

        decoded_res = decode_paper_analyst(
            text=paper_raw,
            title="Submitted Research Paper",
            proposal_context=p_context
        )

        reply = decoded_res.get("formatted_markdown", "")
        if not reply:
            reply = "### 🔬 Paper Decoder (Analyst Mode)\n\nCould not extract sufficient text from the provided paper. Please provide a full abstract or paper text."

        actions = []
        p_mapping = decoded_res.get("proposal_section_mapping", {})
        is_mismatch = p_mapping.get("relevance_status") == "mismatch"

        if not is_mismatch:
            p_stat = p_mapping.get("section_2_1_problem", "")
            if p_stat and not p_stat.startswith("Not reported") and p_stat != "Not applicable.":
                actions.append({
                    "label": "📝 Insert Problem into Sec 2.1",
                    "action": "insert_problem",
                    "content": p_stat
                })
            b_stat = p_mapping.get("section_2_1_baseline", "")
            if b_stat and not b_stat.startswith("Not reported") and b_stat != "Not applicable.":
                actions.append({
                    "label": "📊 Insert Baseline into Sec 2.1",
                    "action": "insert_baseline",
                    "content": b_stat
                })
            g_stat = p_mapping.get("section_2_2_gap", "")
            if g_stat and not g_stat.startswith("None stated") and g_stat != "Not applicable.":
                actions.append({
                    "label": "🔍 Insert Gap into Sec 2.2",
                    "action": "insert_gap",
                    "content": g_stat
                })
            m_stat = p_mapping.get("section_3_2_aim2", "")
            if m_stat and not m_stat.startswith("Not reported") and m_stat != "Not applicable.":
                actions.append({
                    "label": "⚙️ Insert Mechanism into Sec 3.2",
                    "action": "insert_mechanism",
                    "content": m_stat
                })
            c_stat = p_mapping.get("section_4_1_controls", "")
            if c_stat and not c_stat.startswith("Not reported") and c_stat != "Not applicable.":
                actions.append({
                    "label": "🧪 Insert Controls into Sec 4.1",
                    "action": "insert_controls",
                    "content": c_stat
                })
            ms_stat = p_mapping.get("section_5_milestone", "")
            if ms_stat and not ms_stat.startswith("Not reported") and ms_stat != "Not applicable.":
                actions.append({
                    "label": "🎯 Insert Milestones into Sec 5",
                    "action": "insert_milestones",
                    "content": ms_stat
                })
        suggestions = [
            {"text": "⚖️ Evaluate clinical/field generalizability", "prompt": "how generalizable are the findings in this paper?"},
            {"text": "📊 Compare this baseline with our project milestone", "prompt": "compare this paper's baseline to our project target aim"},
            {"text": "🧪 Review positive and negative controls", "prompt": "what positive and negative controls are needed to validate this?"},
            {"text": "✍️ Draft Section 2.2 Literature Gap", "prompt": "help me write the Section 2.2 Literature Gap statement based on this"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "paper_decoder_analyst"
        }

    # WEB SEARCH MODE: Multi-Engine Live Search
    if is_web_search:
        clean_query = search_prefix_match.group(2) if search_prefix_match else text
        clean_query = re.sub(r'^(search (the )?(web|internet|google|online|duckduckgo|engines?)|look up (online|on the web|on google)|find (me )?(papers|studies|articles) online|find online|latest (news|research|paper|development) on)\s*(for|about)?\s*', '', clean_query, flags=re.I).strip()
        if not clean_query:
            clean_query = text

        thinking_steps.append(f"Identified Web & Scholarly Search intent for: '{clean_query}'.")
        thinking_steps.append("Dispatching multi-engine query across DuckDuckGo, Wikipedia, and Europe PMC.")

        search_data = execute_multi_search(clean_query) if execute_multi_search else {"web_results": [], "scholar_results": [], "engine_links": get_search_engine_links(clean_query) if get_search_engine_links else {}}
        web_hits = search_data.get("web_results", [])
        scholar_hits = search_data.get("scholar_results", [])
        engine_links = search_data.get("engine_links", {})

        reply = f"""🌐 **Live Web & Literature Search Dossier: "{clean_query}"**

We queried open web knowledge indices and Europe PMC for the latest developments and reference documentation on **"{clean_query}"**:

---
"""
        if web_hits:
            reply += "### 🌐 Web & Knowledge Base Sources:\n"
            for w in web_hits:
                reply += f"• **[{w['title']}]({w['url']})** *({w['source']})*\n  {w['snippet']}\n\n"

        if scholar_hits:
            reply += "### 📚 Peer-Reviewed Scientific Studies (Europe PMC):\n"
            for s in scholar_hits:
                reply += f"• **[{s['title']}]({s['url']})**\n  *{s['authors']} ({s['year']}) • {s['journal']}*\n  {s['snippet']}\n\n"

        if not web_hits and not scholar_hits:
            reply += f"Direct live search links for **\"{clean_query}\"** across all indexed search engines are compiled below:\n\n"

        reply += "---\n\n### 🚀 One-Click Launch in Search Engines:\n"
        engine_btns = []
        if "google" in engine_links: engine_btns.append(f"[🌐 Google Search]({engine_links['google']})")
        if "scholar" in engine_links: engine_btns.append(f"[📚 Google Scholar]({engine_links['scholar']})")
        if "pubmed" in engine_links: engine_btns.append(f"[🔬 PubMed]({engine_links['pubmed']})")
        if "duckduckgo" in engine_links: engine_btns.append(f"[🦆 DuckDuckGo]({engine_links['duckduckgo']})")
        if "europe_pmc" in engine_links: engine_btns.append(f"[🇪🇺 Europe PMC]({engine_links['europe_pmc']})")
        reply += " • ".join(engine_btns)

        actions = [
            {"label": f"Open in Google: {clean_query[:20]}", "icon": "🌐", "onClickJs": f"window.open('{engine_links.get('google', '#')}', '_blank')"},
            {"label": f"Open in PubMed: {clean_query[:20]}", "icon": "🔬", "onClickJs": f"window.open('{engine_links.get('pubmed', '#')}', '_blank')"},
            {"label": "Formulate Aim for This", "icon": "🎯", "onClickJs": f"quickSendCopilotPrompt('Let us formulate specific aims based on {window_safe_escape(clean_query[:30])}')"}
        ]
        suggestions = [
            {"text": f"💡 What are the bottlenecks in {clean_query[:25]}?", "prompt": f"What are the biophysical bottlenecks in {clean_query}?"},
            {"text": "🎙️ Grill me on this topic", "prompt": f"grill me on {clean_query}"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "web_search",
            "web_results": web_hits,
            "scholar_results": scholar_hits,
            "engine_links": engine_links
        }

    # BT301 ROUTE: Comprehensive Contextual Guidance & Co-Thinking Partner
    elif is_guidance_request:
        thinking_steps.append("Analyzing student inquiry for contextual project guidance & next-step co-thinking.")
        thinking_steps.append(f"Inspecting active proposal draft: Title='{live_title or 'Untitled'}', Chassis='{live_chassis or 'Unspecified'}', Tool='{live_tool or 'Unspecified'}', Target='{live_target or 'Unspecified'}'.")
        thinking_steps.append("Cross-referencing active telemetry against the BT301 Master Workflow (Phases A through E).")
        thinking_steps.append("Formulating structured diagnostic, immediate priority milestone, and concrete scientific worked options.")

        # Analyze Title & Active Telemetry
        lower_lt = (live_title or "").lower().strip()
        is_title_descriptive = bool(re.search(r'^(the\s+)?(effect|role|impact|study|investigation|evaluation|analysis|overview)\s+(of|on|into)\b', lower_lt))
        has_delivery_matrix = any(t in lower_lt for t in ["cream", "gel", "emulsion", "formulation", "ointment", "hydrogel", "topical", "lotion", "nanoparticle", "nanoparticles", "snedds"])
        has_bio_model = any(t in lower_lt for t in [
            "raw 264", "hacat", "hdf", "fibroblast", "keratinocyte", "macrophage", "hepg2", "hek293", "thp-1", "in vitro",
            "balb/c", "c57bl", "wistar", "sprague", "murine", "mice", "mouse", "rat", "rats", "in vivo", "edema",
            "porcine skin", "porcine ear", "franz cell", "franz diffusion", "skin explant", "ex vivo",
            "molecular docking", "molecular dynamics", "in silico", "coli", "pastoris", "yeast", "bacillus"
        ])
        is_title_brief = len((live_title or "").split()) < 6

        title_critique = ""
        if live_title:
            if has_delivery_matrix and not has_bio_model:
                title_critique = f"🔬 **Publication-Grade Title Recommendation for *\"{live_title}\"*:** Your title specifies the delivery matrix ('Cream' / formulation), but does not state the experimental biological chassis (*in vitro* cell line e.g. RAW 264.7 macrophages, *ex vivo* tissue e.g. porcine skin Franz cells, or *in vivo* animal species e.g. BALB/c mice). Specifying your testing model elevates your proposal to publication caliber."
            elif is_title_descriptive:
                title_critique = f"💡 **Title Phrasing Standard for *\"{live_title}\"*:** Your title clearly communicates the research subject, delivery vehicle, and target application. To reach publication standard, lead directly with the active formulation and experimental scope (e.g. *'Formulation and In Vitro Anti-Inflammatory Evaluation of...'*) and state your biological testing chassis."
            elif is_title_brief:
                title_critique = f"⚠️ **Current Title Status:** *\"{live_title}\"* is brief ({len(live_title.split())} words). Reviewers cannot identify your biological testing chassis or quantitative benchmark."
            else:
                title_critique = f"✅ **Scientifically Scoped Title:** *\"{live_title}\"*."
        else:
            title_critique = "⚠️ **Title Status:** You haven't chosen a proposal title yet. We need an active, publication-grade title built on the 4-anchor formula."

        reply = f"""### 🤝 Research Co-Pilot Guidance: Let's Build Your Proposal Step-by-Step

I've examined your active proposal context. Scientific proposal writing can feel complex, but when we follow the **BT301 Master Workflow**, every section builds naturally on the one before it.

---

### 📊 1. Diagnostic of Your Current Draft:
• {title_critique}
• **Strategic Pillars:** Chassis: `{live_chassis or 'Needs Definition'}` | Molecular Tool: `{live_tool or 'Needs Definition'}` | Biological Target: `{live_target or 'Needs Definition'}`

---

### 🎯 2. Your Immediate High-Impact Next Steps (In Priority Order):

1. **Step 1: Lock in Your 4-Part Title & 3 Strategic Pillars (Chapter 14 & 20):**
   **Title Blueprint:** [Active Tool / Construct] in [Host Chassis / Model] to [Quantified Benchmark] for [Target Application]
   *(If your idea is detector/sensor-focused, specify what molecular mechanism it uses, e.g. Cas12a trans-cleavage, electrochemical aptamer, or nano-biosensor).*

2. **Step 2: Define the Literature Gap Pivot (Chapter 8 & 21):**
   State what existing methods can do, and contrast it with their unresolved bottleneck:
   *"Although standard culture assays detect [target], their 48-hour turnaround delays intervention..."*

3. **Step 3: Draft Your Mechanistic Hypothesis & 3 Decoupled Aims (Chapter 9 & 22):**
   State *how* your system works down at the molecular level, followed by 3 independent experimental aims.

---

### ✍️ Three Concrete Worked Directions Tailored to Your Draft:
• **Option A (CRISPR Molecular Diagnostics):**  
  *"Engineered Recombinase Polymerase Amplification (RPA) Coupled with LbCas12a Trans-Cleavage in Paper-Based Lateral Flow Strips to Achieve Sub-Picomolar Pathogen Detection for Rapid Point-of-Care Surveillance"*

• **Option B (Nanomaterial Biosensing):**  
  *"Electrochemical Aptasensor Functionalized with Gold Nanoparticles in Clinical Serum to Attain LOD < 5 pg/mL for Rapid Sepsis Biomarker Quantification"*

• **Option C (Bioactive Formulation & Drug Delivery):**  
  *"Chitosan-PLGA Nanoparticles Loaded with Standardized Bioactive Extract in Human Dermal Fibroblasts to Achieve >80% Wound Closure for Accelerated Tissue Regeneration"*

---

💡 **Where should we start right now?** Tell me which direction fits your vision best, or tell me your target analyte, and we will formulate your exact title and aims together!"""

        actions = [
            {"label": "Suggest & Refine My Title", "icon": "✍️", "onClickJs": "quickSendCopilotPrompt('suggest edits and guide me to write a good title')"},
            {"label": "Draft 3 Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us draft 3 decoupled specific aims')"},
            {"label": "Formulate Literature Gap", "icon": "🔍", "onClickJs": "quickSendCopilotPrompt('help me write a literature gap sentence')"},
            {"label": "Formulate a Sentence (Ch 13)", "icon": "📝", "onClickJs": "quickSendCopilotPrompt('can you help me and guide on how to formulate a sentence')"},
            {"label": "📖 Open BT301 Complete Guide", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(1);"}
        ]

        suggestions = [
            {"text": "✍️ Guide me to write a good title", "prompt": "suggest edits and guide me to write a good title"},
            {"text": "🧬 Help me write my hypothesis sentence", "prompt": "how to write a mechanistic hypothesis sentence"},
            {"text": "🔍 Help me write a literature gap", "prompt": "how to write a literature gap sentence"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_contextual_guidance"
        }

    # BT301 ROUTE: Glossary & Scientific Definition Resolver (Chapter 30)
    elif is_glossary and glossary_match:
        term_name = glossary_match.get("term", text)
        definition = glossary_match.get("definition", "")
        ref = glossary_match.get("ref", "Chapter 30")
        ch_num = glossary_match.get("chapter", 32)

        thinking_steps.append(f"Identified Glossary & Scientific Definition query for: '{term_name}'.")
        thinking_steps.append(f"Cross-referencing definition and practical guidance from {ref}.")
        thinking_steps.append("Synthesizing pedagogical definition card with common pitfalls and actionable next steps.")

        reply = f"""### 📖 Glossary Definition: **{term_name}**
**Curriculum Reference:** {ref}

{definition}

---

### 📐 Standard Proposal Benchmark & Blueprint:
• **Academic Standard:** Ensure this term is quantified with precise physical units (e.g. µM, ng/mL, bp) and clear biological agency.
• **Proposal Integration:** Frame within your active project context ({live_title or "your draft"}) to prevent reviewer ambiguity.

---

### ⚠️ Common Student Pitfall / Reviewer Red Flag:
Confusing this term with colloquial equivalents or related concepts (e.g. technical vs. biological replicates, or aims vs. protocols). Reviewers deduct marks for conceptual imprecision.

---

💡 **Next Steps:** Would you like to check how this applies to your aims, or test your understanding in a mock defense?"""

        actions = [
            {"label": f"Open {ref.split('&')[0].strip()}", "icon": "📖", "onClickJs": f"if(window.openBt301Guide) window.openBt301Guide({ch_num});"},
            {"label": "Open Master Glossary (Ch 30)", "icon": "📚", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(30);"},
            {"label": "Grill Me on This", "icon": "🧠", "onClickJs": f'quickSendCopilotPrompt("grill me on {term_name}")'}
        ]
        suggestions = [
            {"text": f"🔬 How do I apply {term_name} in my aims?", "prompt": f"how do I apply {term_name} in my specific aims?"},
            {"text": f"⚠️ Common reviewer traps for {term_name}?", "prompt": f"what do reviewers look for regarding {term_name}?"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "glossary_definition"
        }

    # BT301 ROUTE: Title Formulation & Rubric Evaluation Coach (Criterion 1)
    elif is_title_coach:
        thinking_steps.append("Identified Project Title Evaluation / Formulation Inquiry (BT_301 Rubric Criterion 1).")
        is_asking_action = bool(re.search(
            r'\b(what\s+.*should\s+(i|we)\s+do|what\s+to\s+do|how\s+to\s+(fix|improve|change|structure)|'
            r'how\s+(should|can)\s+(i|we)|suggest|recommend|rewrite|rephrase|options?|better\s+title|'
            r'what\s+do\s+you\s+think\s+.*(should|do)|withe?\s+(the\s+)?title|with\s+(the\s+)?title|'
            r'how\s+should\s+i\s+fix|how\s+to\s+write)\b',
            lower
        ))
        
        # Determine domain-tailored suggestions
        base_chassis = live_chassis or "Microbial / Biological Model"
        base_tool = live_tool or "Engineered Biosensing / Diagnostic Tool"
        base_target = live_target or "Target Pathogen / Biomarker"
        lower_lt = (live_title or "").lower().strip()

        if "detector" in lower_lt or "detect" in lower_lt:
            t1 = "Engineered RPA-Cas12a Biosensor in Paper Fluidic Strips to Achieve Sub-Picomolar Pathogen Detection for Field-Deployable AMR Surveillance"
            t2 = "Field-Deployable Paper-Based Fluorometric Detector for Rapid (<30 min) Diagnostic Surveillance of Antimicrobial Resistance"
            t3 = "Optimization and Analytical Validation of a Multiplexed crRNA-Cas12a System for Colistin Resistance Gene (mcr-1) Detection"
        elif any(k in lower_lt for k in ["cream", "calendula", "plant", "extract", "wound", "ointment"]):
            t1 = "Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized Calendula Cream in RAW 264.7 Macrophages Benchmarked Against Hydrocortisone 1%"
            t2 = "Thermosensitive Pluronic F-127 Hydrogel Loaded with Standardized Botanical Extract in Human Dermal Fibroblasts to Attain >80% Wound Closure"
            t3 = "Self-Nanoemulsifying Drug Delivery System (SNEDDS) of Standardized Bioactive Fraction Across Porcine Skin to Achieve >70% Transdermal Permeation"
        else:
            t1 = f"Engineered {base_tool} in {base_chassis} to Achieve High-Affinity Sub-Nanomolar Target Binding for Precision Bio-Intervention"
            t2 = f"Thermostabilized {base_tool} Immobilized in {base_chassis} Matrix to Attain >85% Catalytic Turnover for Continuous Bioprocessing"
            t3 = f"Nanoparticle-Formulated {base_tool} in {base_chassis} to Achieve Rapid Field-Deployable Detection of {base_target}"

        if is_asking_action and live_title:
            reply = f"""### 💡 Recommended Next Steps for Your Title: *"{live_title}"*

To turn this into a fundable, publication-grade proposal title, replace the passive phrasing with your **active intervention**, **biological chassis/model**, and **measurable quantitative goal**:

---

### 📐 3 Publication-Ready Title Options Tailored to Your Project:

1. **Analytical & Mechanism-Focused:**
   > **"{t1}"**
   *Why reviewers like it:* Clearly defines the active tool, the exact target affinity, and the precise diagnostic scope.

2. **Field-Ready / Translational Platform:**
   > **"{t2}"**
   *Why reviewers like it:* Emphasizes practical turnaround time (<30 min), field-readiness, and the clinical/environmental application.

3. **Optimization & Analytical Validation:**
   > **"{t3}"**
   *Why reviewers like it:* Grounds the work in molecular optimization with rigorous analytical validation.

---

### ✏️ Quick Action:
Click **Adopt Title 1**, **Adopt Title 2**, or **Jump to Step 1** below to apply one of these titles directly to your proposal!"""

            actions = [
                {"label": "Adopt Title 1", "icon": "✨", "onClickJs": f"if(window.copilotAdoptTitle) window.copilotAdoptTitle('{t1}');"},
                {"label": "Adopt Title 2", "icon": "🚀", "onClickJs": f"if(window.copilotAdoptTitle) window.copilotAdoptTitle('{t2}');"},
                {"label": "Jump to Step 1: Title Input", "icon": "✏️", "onClickJs": "jumpToEditorSection('proposal-title-input')"},
                {"label": "Inspect 3 Strategic Pillars", "icon": "🏷️", "onClickJs": "jumpToEditorSection('pillar-chassis')"}
            ]
            suggestions = [
                {"text": "🎯 How to draft Specific Aims for this title?", "prompt": "Let us review and draft 3 specific aims for this title"},
                {"text": "🧪 What experimental controls are required?", "prompt": f"what controls are needed for {live_title}"}
            ]
            return {
                "reply": reply,
                "actions": actions,
                "suggestions": suggestions,
                "thinking": thinking_steps,
                "concept": "title_formulation"
            }
        thinking_steps.append(f"Auditing current title '{live_title or 'Untitled'}' against active engineering mechanism, biological chassis, and quantitative milestone requirements.")
        thinking_steps.append(f"Tailoring title guidance to active topic domain: {live_title or 'Active Project'}.")

        # Detect topic domain
        combined_topic = f"{live_title} {live_chassis} {live_tool} {live_target} {text}".lower()
        is_phyto = bool(re.search(r'\b(calendula|marigold|plant|herb|extract|phytochem|topical|cream|ointment|gel|skin|dermal|wound|erythema)\b', combined_topic))
        is_amr = bool(re.search(r'\b(mrsa|antimicrobial|antibiotic|pathogen|mic|biofilm|nanoparticle)\b', combined_topic)) and not is_phyto
        is_comp = bool(re.search(r'\b(docking|molecular dynamics|virtual screening|binding affinity|in silico)\b', combined_topic))

        # Title evaluation
        lower_lt = (live_title or "").lower().strip()
        is_descriptive = bool(re.search(r'^(the\s+)?(effect|role|impact|study|investigation|evaluation|analysis|overview)\s+(of|on|into)\b', lower_lt))
        has_delivery_matrix = any(t in lower_lt for t in ["cream", "gel", "emulsion", "formulation", "ointment", "hydrogel", "topical", "lotion", "nanoparticle", "nanoparticles", "snedds"])
        has_bio_model = any(t in lower_lt for t in [
            "raw 264", "hacat", "hdf", "fibroblast", "keratinocyte", "macrophage", "hepg2", "hek293", "thp-1", "in vitro",
            "balb/c", "c57bl", "wistar", "sprague", "murine", "mice", "mouse", "rat", "rats", "in vivo", "edema",
            "porcine skin", "porcine ear", "franz cell", "franz diffusion", "skin explant", "ex vivo",
            "molecular docking", "molecular dynamics", "in silico", "coli", "pastoris", "yeast", "bacillus"
        ])
        has_num = bool(re.search(r'\b(\d+%|>\s*\d+|<\s*\d+|mic\b|ic50\b|kd\b|hydrocortisone|closure|comparator|benchmarked)\b', lower_lt))
        wc = len((live_title or "").split())

        critique_header = ""
        if live_title:
            critique_header = f"### 🔍 Rubric Evaluation of Your Current Title:\n> **\"{live_title}\"**\n\n"
            if has_delivery_matrix and not has_bio_model:
                critique_header += (
                    "🔬 **Publication-Grade Scientific Recommendation (Chassis vs. Delivery Vehicle):**\n"
                    "Your title specifies the delivery matrix (*'Cream'* / formulation), but does not state the experimental biological chassis. "
                    "In scientific research papers, *'Cream'* is the dosage vehicle, not the biological testing model. Reviewers and grant panels must know whether testing is:\n"
                    "• **In Vitro:** Naming the exact cell line (e.g. *'in RAW 264.7 Macrophages'* or *'in HaCaT Keratinocytes'*)\n"
                    "• **Ex Vivo:** Naming the tissue model (e.g. *'across Porcine Skin in Franz Diffusion Cells'*)\n"
                    "• **In Vivo:** Naming the animal species/strain (e.g. *'in a BALB/c Murine Edema Model'*)\n"
                    "• **In Silico:** Naming the computational target (e.g. *'via Molecular Docking against COX-2'*)\n\n"
                )
            if is_descriptive:
                critique_header += (
                    "💡 **Publishing Phrasing Standard:** Leading with descriptive phrasing (*\"Study of...\"* or *\"The effect of...\"*) successfully identifies your research subject, but peer-reviewed papers lead directly with the active intervention and scope "
                    "(e.g. *'Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized Calendula Cream in RAW 264.7 Macrophages'*).\n\n"
                )
            if not has_num:
                critique_header += "⚠️ **Target Benchmark / Comparator Suggestion:** High-scoring titles state a measurable endpoint or clinical reference comparator (e.g. *'Benchmarked Against Hydrocortisone 1%'*, *'>80% Wound Closure'*, *'MIC < 15 µg/mL'*).\n\n"
            if wc < 6:
                critique_header += f"⚠️ **Missing Key Details ({wc} words):** Your title is brief; reviewers cannot identify your biological model or specific application.\n\n"
            elif not is_descriptive and has_bio_model and has_num and wc >= 7:
                critique_header += "✅ **Publication-Grade Foundation:** Your title avoids passive phrasing, specifies an explicit biological chassis, and includes a quantitative milestone.\n\n"
            critique_header += "---\n\n"

        if is_phyto:
            matched_bioactive = re.search(r'\b(calendula(?:\s+officinalis)?|aloe(?:\s+vera)?|curcumin|turmeric|chamomile|neem|nigella(?:\s+sativa)?|boswellia(?:\s+serrata)?|thyme|tea\s+tree|green\s+tea|eucalyptus|propolis|quercetin|resveratrol|thymol|carvacrol|rutin)\b', lower_lt, re.I)
            active_name = matched_bioactive.group(0).title() if matched_bioactive else (live_tool or "Standardized Botanical Extract")
            matched_vehicle = re.search(r'\b(cream|gel|emulsion|nano-emulsion|hydrogel|ointment|lotion|ethosome|liposome|nanoparticles?)\b', lower_lt, re.I)
            vehicle_name = matched_vehicle.group(0).title() if matched_vehicle else "Formulation"

            domain_heading = f"🌿 **Phytochemical & Topical Bioactive Publication Tracks for {active_name}:**"
            domain_models = (
                f"• **Track 1 (In Vitro Cell Line):** *Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized {active_name} {vehicle_name} in RAW 264.7 Macrophages Benchmarked Against Hydrocortisone 1%*\n"
                f"• **Track 2 (Ex Vivo Skin Barrier):** *Formulation, Physicochemical Characterization, and Ex Vivo Transdermal Permeation of Standardized {active_name} {vehicle_name} Across Porcine Ear Skin*\n"
                f"• **Track 3 (In Vivo Animal Model):** *Formulation and In Vivo Preclinical Anti-Inflammatory Efficacy of Standardized {active_name} {vehicle_name} in a BALB/c Murine Edema Model*"
            )
        elif is_amr:
            domain_heading = "🛡️ **Antimicrobial & Resistance Countermeasure Blueprint:**"
            domain_models = (
                "• *Biosynthesized Silver Nanoparticles in Electrospun PCL Wound Dressings to Achieve MIC < 10 µg/mL for Methicillin-Resistant Staphylococcus aureus*\n"
                "• *Engineered Endolysin-Antimicrobial Peptide Chimera in Pseudomonas aeruginosa to Achieve >3-Log Biofilm Reduction*"
            )
        else:
            domain_heading = "🔬 **Precision Biotechnology Blueprint:**"
            domain_models = (
                f"• *Engineered {live_tool or 'Molecular Construct'} in {live_chassis or 'Target Host'} to Achieve Sub-Nanomolar Target Binding for Precision Therapy*\n"
                f"• *Nanoparticle-Formulated {live_tool or 'Active Agent'} in {live_chassis or 'Biological Model'} to Attain >85% Efficacy against {live_target or 'Target Endpoint'}*"
            )

        reply = f"""{critique_header}### 🏷️ BT_301 Project Title Formulation Guide (Criterion 1)

In biotechnology research proposals, your title is your first impression. It must describe an **active engineering solution**, not a passive classroom observation.

---

### 📐 The 4-Anchor Title Formula:
**Title Blueprint:** [Active Tool / Extract] in [Delivery Matrix] evaluated in [Biological Chassis] to [Target Benchmark] for [Real-World Problem]

1. **Active Tool / Intervention:** What specific molecule, standardized botanical extract, or engineered construct are you deploying?
2. **Delivery Matrix / Formulation:** What topical cream, hydrogel, or nanoemulsion vehicle?
3. **Biological Chassis / Testing Model:** What exact cell line (*in vitro* e.g. RAW 264.7 macrophages), animal species (*in vivo* e.g. BALB/c mice), or tissue model (*ex vivo* e.g. porcine skin)?
4. **Target Benchmark / Comparator:** What quantitative milestone or reference standard (e.g. *benchmarked against Hydrocortisone 1% cream*, *>80% wound closure*, *MIC < 15 µg/mL*)?
5. **Clinical / Environmental Application:** What exact disease or real-world problem are you resolving?

---

### {domain_heading}
{domain_models}

---

💡 **Next Step for You:** Draft an updated title using the 4-anchor formula in Section 1 of the editor, then click **"Check My Reasoning"** to verify!"""

        actions = [
            {"label": "Jump to Title in Editor", "icon": "✏️", "onClickJs": "jumpToEditorSection('proposal-title-input');"},
            {"label": "Inspect 3 Strategic Pillars", "icon": "🏷️", "onClickJs": "jumpToEditorSection('pillar-chassis');"}
        ]
        suggestions = [
            {"text": "💡 How do I pick a measurable milestone for my title?", "prompt": "how to choose a measurable target benchmark for my title"},
            {"text": "🏷️ Help me align my 3 pillars with my title", "prompt": "how do the 3 strategic pillars map to the project title?"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "title_formulation"
        }

    # BT301 ROUTE: Specific Aims Formulation Coach (Chapter 9 & 22)
    elif is_aims_coach:
        thinking_steps.append("Identified Specific Aims Formulation & Review Inquiry (BT301 Guide • Chapter 9 & 22).")
        thinking_steps.append("Evaluating Section 3 Objectives against decoupling, action verbs, and quantitative endpoints.")

        live_objs = str((proposal_context or {}).get("objectives") or (proposal_context or {}).get("aim") or "").strip()
        is_asking_audit = bool(re.search(r'\b(think|review|check|evaluate|rate|critique|audit|feedback|how\s+are|how\s+is|good|ok|problem|missing|fix|status|what\s+do\s+you\s+think)\b', lower)) or ("objective" in lower or "aim" in lower)

        if is_asking_audit:
            if len(live_objs) < 30:
                reply = f"""### 🎯 Evaluation of Section 3: Specific Objectives & Aims

Your Section 3.2 Specific Objectives are currently **blank or nascent** ({len(live_objs.split())} words declared).

In BT_301, academic grant reviewers look for **3 independent, verb-led research milestones** that test your central hypothesis rather than routine laboratory protocol steps.

---

### 📐 Recommended 3-Aim Framework Tailored to Your Project (*"{live_title or 'Active Proposal'}"*):

• **Specific Objective 1 (Molecular Tool Engineering & crRNA Optimization):**
  > *"Engineer and screen crRNA constructs for RPA-Cas12a complexation to achieve high-affinity target recognition of the target biomarker."*

• **Specific Objective 2 (In Vitro Bench Validation & Aim Decoupling):**
  > *"Characterize trans-cleavage kinetics and establish the Limit of Detection (LoD < 10 pM) using a synthetic positive standard and matrix-matched negative controls."*

• **Specific Objective 3 (Authentic Matrix Performance & Translational Assay):**
  > *"Validate detector specificity and recovery rate (>90%) in authentic clinical or environmental specimens against PCR gold standards."*

---

### 🛡️ Key Decoupling Rule (Chapter 9 §9.4):
Ensure **Objective 2 does not collapse** if Objective 1 produces lower yields (use synthetic controls or commercial reference standards while engineered variants are in production)."""
            else:
                has_decoupled = not bool(re.search(r'\b(if aim 1 works|following successful completion of aim 1|pending positive results in aim 1)\b', live_objs.lower()))
                has_action_verbs = bool(re.search(r'\b(engineer|quantify|validate|characterize|optimize|decouple|formulate|synthesize|screen)\b', live_objs.lower()))
                has_num_metric = bool(re.search(r'(\d+%|>\s*\d+|<\s*\d+|lod\b|cv\s*<|p\s*<|µg/ml|pm\b|nm\b|recovery)', live_objs.lower()))

                reply = f"""### 🔍 Audit of Your Current Section 3.2 Specific Objectives:

**Analyzed Draft ({len(live_objs.split())} words):**
> *"{live_objs[:200]}..."*

---

### 📋 BT_301 Grant Rubric Evaluation:
1. **Decoupled Architecture (Chapter 9 §9.4):** {('✅ **Decoupled** (No Domino Collapse trap detected).' if has_decoupled else '⚠️ **Risk of Domino Collapse:** Ensure Objective 2 can proceed even if Objective 1 encounters yield delays.')}
2. **Approved Action Verbs:** {('✅ **Active & Mechanistic** (Uses approved action verbs like Engineer, Quantify, Validate).' if has_action_verbs else '⚠️ **Needs Stronger Verbs:** Replace passive verbs (*Study, Investigate, Explore*) with milestone verbs (*Quantify, Characterize, Optimize*).')}
3. **Quantitative Endpoints (Chapter 22):** {('✅ **Quantified** (Contains explicit quantitative benchmarks/units).' if has_num_metric else '⚠️ **Missing Numerical Benchmark:** Every objective must state a target number (e.g. *LoD < 10 pM*, *yield > 85%*, *recovery 95–105%*).')}
4. **Section 4 Assay Traceability:** Every objective above must map 1:1 to an assay work package in Section 4.1.

---

💡 **Recommended Next Step:** Click **Open Scientific Consistency Matrix** below to verify Objective-to-Method alignment!"""

            actions = [
                {"label": "Jump to Step 3: Specific Aims", "icon": "🎯", "onClickJs": "jumpToEditorSection('section-3-2-objectives')"},
                {"label": "Open Scientific Consistency Matrix", "icon": "🧭", "onClickJs": "if(window.runScientificConsistencyEngine) window.runScientificConsistencyEngine(true);"},
                {"label": "Open Chapter 22: Specific Aims Guide", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(22);"}
            ]
            suggestions = [
                {"text": "🧪 What controls do I need for these aims?", "prompt": "what controls are needed for my specific aims?"},
                {"text": "🧭 Check Objective-to-Method consistency", "prompt": "check scientific consistency between objectives and methods"}
            ]
            return {
                "reply": reply,
                "actions": actions,
                "suggestions": suggestions,
                "thinking": thinking_steps,
                "concept": "objectives_audit"
            }

        reply = f"""### 🎯 BT301 Specific Aims Formulation Guide (Chapter 9 & 22)

A Specific Aim is **not a methodology step** (e.g., *"To run PCR"* or *"To purify protein"*). An aim is a **verb-led scientific milestone** that directly tests one logical component of your mechanistic hypothesis.

---

### 📐 The Universal 4-Part Specific Aim Formula:
**Specific Aim Blueprint:** [Action Verb] + [Target Molecule / System] + [Mechanistic Method] + [Chassis / Model] + [Quantified Endpoint]

• **Approved Action Verbs:** *Quantify, Engineer, Validate, Characterize, Optimize, Decouple, Formulate.*  
• **Prohibited Verbs:** *Study, Investigate, Explore, Look into, Understand.*

---

### 🛡️ The Non-Negotiable Decoupling Rule (Chapter 9 §9.4):
Reviewers immediately reject proposals where Aim 2 cannot proceed if Aim 1 fails or yields low expression.
• **Bad (Coupled):** Aim 1 produces an engineered enzyme; Aim 2 tests its activity on plastic. If Aim 1 yield is poor, Aim 2 is dead.
• **Good (Decoupled):** Aim 2 uses commercially available wild-type enzyme as an active benchmark while Aim 1 variants are in production.

---

### 📑 Alignment Matrix Checklist (Chapter 22):
Every aim must explicitly declare:
1. **Biological Hypothesis Tested**
2. **Standardized Quantitative Assay** (e.g., HPLC, qPCR, ELISA, IC50)
3. **Primary Positive Standard & Matrix Blank**
4. **Technical Feasibility & Milestone Benchmarks**"""

        actions = [
            {"label": "Open Chapter 9: The Funnel", "icon": "🎯", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(9);"},
            {"label": "Open Chapter 22: Specific Aims", "icon": "📑", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(22);"},
            {"label": "Draft 3 Decoupled Aims for My Project", "icon": "✍️", "onClickJs": "quickSendCopilotPrompt('Let us draft 3 decoupled specific aims for my active proposal')"}
        ]
        suggestions = [
            {"text": "🎯 Draft Aim 1 for my project", "prompt": "draft Aim 1 for my active proposal"},
            {"text": "🛡️ How to decouple Aim 2 from Aim 1?", "prompt": "how to decouple Aim 2 from Aim 1?"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "aims_formulation"
        }

    # BT301 ROUTE: Methodology & Experimental Design Audit Coach (Chapter 9 & 23)
    elif is_methodology_coach:
        thinking_steps.append("Identified Methodology & Experimental Rigor Audit Inquiry (BT301 Guide • Chapter 9 & 23).")
        thinking_steps.append("Auditing Section 4 against 5 universal pillars: constructs, conditions, quantitative assays, controls, and statistics.")

        live_meth = str((proposal_context or {}).get("methodology") or "").strip()
        has_construct_or_source = bool(re.search(r'\b(primer|plasmid|vector|gibson|strain|atcc|extract|synthesis|formulat|nanoparticle|sequence|accession|reagent|sigma|thermo)\b', live_meth, re.I))
        has_prep_or_culture = bool(re.search(r'\b(culture|incubat|induc|iptg|purif|lysis|centrifug|filtrat|macerat|sonicat|homogeniz|buffer|ph\s*\d|°c)\b', live_meth, re.I))
        has_quant_assay = bool(re.search(r'\b(assay|elisa|qpcr|pcr|dpph|abts|mic|mbc|sds-page|western|hplc|gc-ms|dls|fluor|absorbance|od\s*\d+|nm\b|ic50|kcat|km\b|cleavage)\b', live_meth, re.I))
        has_pos_ctrl = bool(re.search(r'\b(positive\s+control|reference\s+standard|ascorbic\s+acid|trolox|dexamethasone|ciprofloxacin|commercial\s+standard|hydrocortisone)\b', live_meth, re.I))
        has_neg_ctrl = bool(re.search(r'\b(negative\s+control|vehicle\s+control|untransformed|empty\s+vector|blank|ntc|untreated)\b', live_meth, re.I))
        has_stats = bool(re.search(r'\b(anova|t-test|tukey|probit|lod|limit of detection|confidence interval|sd\b|sem\b|p\s*<\s*0\.05|graphpad|nonlinear regression|4pl)\b', live_meth, re.I))
        has_triplicates = bool(re.search(r'\b(triplicate|biological\s+replicate|technical\s+replicate|n\s*=\s*[3-9])\b', live_meth, re.I))

        words_count = len(live_meth.split())
        reply = f"""🔵 **Evidence Status:** `[Live Proposal Diagnostic — Section 4 & Scientific Consistency Engine]`

🧪 **Laboratory Methodology & Experimental Design Audit (Section 4):**

Your current Section 4.1 Methodology ({words_count} words declared) was evaluated across the **5 universal experimental design pillars**:

1. **Construct, Biological Source & Reagent Specification:** {'✅ **Declared** (Strains, constructs, or chemical/biological sources specified).' if has_construct_or_source else '⚠️ **Missing/Under-specified** (Specify host strain/ATCC number, vector/primer sequences, or reagent grade/source).'}
2. **Upstream Sample Processing, Culture & Conditions:** {'✅ **Declared** (Incubation temperatures, buffers, pH, or extraction/purification steps included).' if has_prep_or_culture else '⚠️ **Missing/Under-specified** (Detail physical parameters: temperature in °C, pH, molarity, incubation duration, and extraction/purification protocol).'}
3. **Quantitative Analytical Assay & Readout Unit:** {'✅ **Declared** (Specific bioassay and quantitative measurement unit identified).' if has_quant_assay else '⚠️ **Missing/Under-specified** (State the exact analytical instrument/assay and quantitative unit, e.g., OD wavelength in nm, IC50, MIC in µg/mL, or LoD).'}
4. **Experimental Controls (Positive & Matrix-Matched Negative):** {'✅ **Verified** (Both positive reference standard and negative/vehicle baseline declared).' if (has_pos_ctrl and has_neg_ctrl) else f"⚠️ **Incomplete** — Positive Control: {'✅' if has_pos_ctrl else '❌ Missing'} | Negative/Vehicle Control: {'✅' if has_neg_ctrl else '❌ Missing'}"}
5. **Replicate Architecture & Statistical Analysis:** {'✅ **Verified** (Independent biological/technical replicates and statistical test declared).' if (has_triplicates and has_stats) else f"⚠️ **Incomplete** — Replicates: {'✅' if has_triplicates else '❌ Specify biological vs. technical replicates (n=3)'} | Statistical Test: {'✅' if has_stats else '❌ Specify ANOVA / t-test / Probit / 4PL regression'}"}

---

💡 **Recommended Next Step:** Click **Open Scientific Consistency Matrix** below to inspect Objective-to-Method alignment or **Sync Objectives → Table 2** to populate your Experimental Design Matrix!"""

        actions = [
            {"label": "Open Scientific Consistency Matrix", "icon": "🧭", "onClickJs": "if(window.runScientificConsistencyEngine) window.runScientificConsistencyEngine(true);"},
            {"label": "Sync Objectives → Table 2 Matrix", "icon": "🔄", "onClickJs": "if(window.autoPopulateTable2FromObjectives) window.autoPopulateTable2FromObjectives();"},
            {"label": "Insert Verified Controls", "icon": "🧪", "onClickJs": "if(window.copilotAdoptControls) window.copilotAdoptControls();"},
            {"label": "Jump to Step 4: Methodology", "icon": "✏️", "onClickJs": "jumpToEditorSection('section-4-1-methodology');"}
        ]
        suggestions = [
            {"text": "🧪 What negative controls should we design?", "prompt": "What negative controls should we design?"},
            {"text": "🧭 Check Objective-to-Method consistency", "prompt": "check scientific consistency between objectives and methods"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "methodology_audit"
        }

    # BT301 ROUTE: Unique Selling Points (USPs) & Ansoff Matrix Coach (Chapter 25)
    elif is_usp_coach or is_ansoff_coach:
        thinking_steps.append("Identified Strategic Positioning & USP / Ansoff Inquiry (BT301 Guide • Chapter 25).")
        thinking_steps.append("Verifying that USP is established prior to Ansoff quadrant categorization.")
        thinking_steps.append("Enforcing the 3-part winning USP formula and flagging strawman competitors.")

        tool_disp = live_tool or "proposed bio-engineered solution"
        target_disp = live_target or "target indication"

        reply = f"""### ⭐ BT301 Strategic Positioning: USPs & Ansoff Matrix (Chapter 25)

In academic biotechnology proposals, **you cannot decide your Ansoff quadrant until you define your Unique Selling Points (USPs)**. Reviewers look for clear proof of why clinicians, industry, or researchers would choose your technology over existing standards.

---

### ⚠️ The "Strawman Competitor" Trap
Reviewers instantly penalize proposals comparing against vague, fictional competitors:
* ❌ **REJECTED (Strawman):** *"Unlike traditional methods which are slow and expensive, our method is fast and green."*
* ✅ **ACCEPTED (Real Benchmark):** *"Unlike conventional broth microdilution AST which delays results by 48 hours, our CRISPR-Cas12a fluorescent assay detects colistin resistance markers directly from clinical isolates within 45 minutes at 37 °C."*

Always name the **exact commercial standard** or gold standard protocol (e.g. *TaqMan RT-qPCR*, *topical hydrocortisone 1% cream*, *wild-type PETase*, *silica-column extraction*).

---

### 📐 The Winning 3-Part Biotechnology USP Formula
Construct your proposal's USP using this exact sentence structure:
> **"Unlike [Named Commercial Benchmark / Gold Standard], our [{tool_disp}] [Specific Mechanistic / Technical Advantage], achieving [Quantifiable Performance Metric] and providing [Concrete Stakeholder / Clinical Benefit]."**

---

### 🧭 How Your USP Dictates Your Ansoff Quadrant
Once your USP is written, your Ansoff quadrant becomes clear:
1. **Market Penetration (Existing Tech • Existing Market):**  
   Your USP is cost-reduction, import substitution, or local sourcing for an already-established product.
2. **Product Development (Novel Tech • Existing Market) — Most Common in BT301:**  
   Your USP is a novel bio-engineered construct/formulation (e.g. ethosomal nanocarrier, CRISPR diagnostic) replacing an existing suboptimal treatment/test for a known disease.
3. **Market Development (Existing Tech • New Market):**  
   Taking an established clinical technology into a completely new sector (e.g. lateral flow strips repurposed for agricultural soil testing).
4. **Diversification (New Tech • New Market):**  
   Radical frontier innovation creating a completely new market (highest technical and commercial risk)."""

        actions = [
            {"label": "Jump to USP Card in Proposal Studio", "icon": "⭐", "onClickJs": "if(window.goToStep) { window.goToStep(3); setTimeout(() => { const el = document.getElementById('card-section-usp'); if(el) el.scrollIntoView({behavior: 'smooth', block: 'center'}); }, 300); }"},
            {"label": "Open Chapter 25 Guide", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(25);"},
            {"label": "Audit My USP Now", "icon": "🔬", "onClickJs": "quickSendCopilotPrompt('audit my USP and check for strawman competitors')"}
        ]
        suggestions = [
            {"text": "🌿 Show Natural Extract USP formula", "prompt": "show me a winning USP example for natural botanical extract nanogel"},
            {"text": "🔬 Show CRISPR Diagnostic USP formula", "prompt": "show me a winning USP example for CRISPR biosensor diagnostic"},
            {"text": "📊 How do I choose my Ansoff quadrant?", "prompt": "how to choose the right Ansoff quadrant for my biotechnology proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking_steps": thinking_steps,
            "confidence": 0.95,
            "concept": "usp_ansoff_market"
        }

    # BT301 ROUTE: Table 2 & Scientific Consistency Coach (Chapter 26)
    elif is_results_table_coach or is_consistency_matrix_coach:
        thinking_steps.append("Identified Table 2 Expected Results & Scientific Consistency Inquiry (BT301 Guide • Chapter 26).")
        thinking_steps.append("Enforcing publication-grade 5-column table architecture and Aim → Method → Control → Outcome alignment.")

        tool_disp = live_tool or "proposed bio-engineered solution"
        target_disp = live_target or "target indication"

        reply = f"""### 📊 BT301 Section 5.2 Table 2: Publication Benchmark & Interactive Table Formulator

### 🎯 What is the Aim of Table 2 in a Proposal?
In a research proposal, you have **not yet generated laboratory results**. Therefore, reviewers (evaluators, grant panels, thesis committees) require a pre-registered **falsifiability protocol**:
1. **Prevents HARKing (Hypothesizing After Results are Known):** Commits the researcher to specific quantitative thresholds *before* spending grant funds.
2. **Defines Objective Project Success vs. Failure:** Distinguishes between what is merely "interesting" and what empirically proves the scientific hypothesis.
3. **Quantitative Milestone Evaluation:** If the acceptance criterion in Column 5 is evaluated, it provides empirical proof of whether technical benchmarks have been met.
4. **Ensures 1-to-1 Traceability:** Bridges Section 3.2 (Specific Objectives) and Section 4 (Methodology) directly to empirical deliverables.

---

### 📋 The 5 Publication-Grade Benchmark Columns
Top peer-reviewed biotechnology journals (*Nature Biotechnology*, *ACS Synthetic Biology*, *Phytomedicine*) require results tables with these 5 core components:
1. **Target / Parameter (Linked to Specific Objective):** Identifies the exact molecular, physicochemical, or diagnostic readout (e.g. *1. Flavonoid Yield*, *2. Ethosome Size & PDI*, *3. Analytical Sensitivity LoD*).
2. **Assay Method & Experimental Condition:** Specifies the analytical instrument, temperature, wavelength, or reaction setup (e.g. *HPLC-DAD at 360 nm, 60 °C*, *DLS at 25 °C*, *Sandwich ELISA at 450 nm*).
3. **Baseline / Comparator Standard:** Specifies the negative baseline and positive gold-standard control without which numbers have zero scientific meaning (e.g. *Conventional maceration (12.4 mg/g)*, *Dexamethasone positive control (10 µM)*).
4. **Anticipated Quantitative Value (with Units & ± SD):** Grounds your expectation in preliminary data or peer-reviewed literature with explicit variance (e.g. *38.5 ± 2.1 mg/g dry wt*, *PDI = 0.18 ± 0.02*).
5. **Acceptance Criterion & Statistical Significance:** Pre-commits to the mathematical threshold defining success (e.g. *≥ 3.0-fold yield increase over baseline (p < 0.01, ANOVA)*).

---

### 📐 Interactive Table Formulator: Add Custom Rows & Columns
Because different biotechnology domains or university formats require custom table structures, you have complete freedom to formulate Table 2:
* **➕ Add Row:** Add custom rows for additional experiments or analytical phases.
* **➕ Add Column:** Add extra columns using 1-click academic presets (*Statistical Test & Hypothesis*, *Sample Size & Replicates n=*, *Literature Benchmark DOI*, *Timeline Quarter*, *Responsible Station*) or type your own custom header name!
* **✏️ Rename Headers:** Click the pencil icon on any column to customize its name.
* **✕ Remove Columns:** Click ✕ on any header to delete unwanted columns (maintains min 2 columns).
* **🏛️ 1-Click Layout Presets:** Switch anytime between:
  - **5-Col Standard:** Publication benchmark (Target, Method, Comparator, Value, Criterion).
  - **4-Col Classic:** Classical proposal format (Objective, Metric, Method, Criterion).
  - **6-Col High-Rigor:** Adds dedicated statistical hypothesis test and sample power (n =).
* **🪄 Auto-Fill from Objectives:** Analyzes your Section 3.2 text and automatically fills rows with topic-tailored parameters!"""

        actions = [
            {"label": "Jump to Section 5.2 Table 2", "icon": "📊", "onClickJs": "if(window.goToStep) { window.goToStep(2); setTimeout(() => { const el = document.getElementById('expected-results-table'); if(el) el.scrollIntoView({behavior: 'smooth', block: 'center'}); }, 300); }"},
            {"label": "Open Scientific Consistency Matrix", "icon": "🧭", "onClickJs": "if(window.goToStep) { window.goToStep(2); setTimeout(() => { const el = document.getElementById('scientific-consistency-engine-card'); if(el) el.scrollIntoView({behavior: 'smooth', block: 'center'}); }, 300); }"},
            {"label": "Open Chapter 26 Guide", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(26);"}
        ]
        suggestions = [
            {"text": "🌿 Show Natural Extract Table 2 example", "prompt": "show me an example of Table 2 for natural botanical extract and formulation"},
            {"text": "🧬 Show Recombinant Enzyme Table 2 example", "prompt": "show me an example of Table 2 for recombinant enzyme engineering"},
            {"text": "🔬 Show CRISPR Diagnostic Table 2 example", "prompt": "show me an example of Table 2 for CRISPR molecular diagnostic assay"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking_steps": thinking_steps,
            "confidence": 0.95,
            "concept": "table2_consistency_matrix"
        }

    # BT301 ROUTE: Grant Budgeting in EGP Coach (Chapter 25)
    elif is_budget_coach:
        thinking_steps.append("Identified Grant Budgeting & Financial Feasibility Inquiry (BT301 Guide • Chapter 25).")
        thinking_steps.append("Enforcing 100% Egyptian Pounds (EGP) currency mandate and 4-tier category allocation.")
        thinking_steps.append("Generating itemized justification blueprint and reviewer compliance checks.")

        reply = """### 💰 BT301 Itemized Grant Budget Guide (Chapter 25)

In Egyptian academic funding (STDF, ASRT, University Grants), all budgets **MUST be denominated in Egyptian Pounds (EGP)**. Ensure every direct cost line item uses EGP with explicit local quotes and conversion documentation.

---

### 📊 The 4 Standard Grant Budget Categories:
1. **Category 1: Direct Reagents & Assay Consumables (50–60% of total):**  
   Enzymes, primers, antibodies, cell culture media, plasticware, specialized assay kits.
2. **Category 2: Core Facility Testing & Analytical Services (20–25% of total):**  
   Per-sample charges for Sanger sequencing, LC-MS/MS, TEM/SEM imaging, NMR, FACS.
3. **Category 3: Student & Personnel Stipends (10–15% of total):**  
   Undergraduate/MSc student research compensation allocated per semester.
4. **Category 4: Contingency & Buffer Reserve (5–10% of total):**  
   Emergency buffer for customs clearance, currency fluctuation, and re-runs.

---

### 📝 The Reagent Justification Formula (Chapter 25 §25.3):
Reviewers reject vague line items like *"Chemicals: 50,000 EGP"*. Every single item must be mathematically justified:
**Total Cost (EGP)** = [Number of Samples] × [3 Biological Replicates] × [Unit Price per Reaction (EGP)]

• **Example:** *TaqPath qPCR Master Mix (Applied Biosystems, Cat# A15297): 480 reactions across 40 samples × 3 replicates × 4 target genes = 4 kits @ 12,500 EGP/kit = 50,000 EGP.*"""

        actions = [
            {"label": "Open Chapter 25: Itemized Budget", "icon": "💰", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(25);"},
            {"label": "Audit My Current Budget", "icon": "📊", "onClickJs": "quickSendCopilotPrompt('audit my proposal budget in EGP')"}
        ]
        suggestions = [
            {"text": "💵 How to justify reagent costs?", "prompt": "how to write a reagent justification in EGP"},
            {"text": "🛡️ What is the maximum budget allowed?", "prompt": "what are the standard budget limits for student proposals?"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "budget_formulation"
        }

    # BT301 ROUTE: Milestone Timeline & Gantt Chart Coach (Chapter 24)
    elif is_timeline_coach:
        thinking_steps.append("Identified Milestone Timeline & Gantt Chart Inquiry (BT301 Guide • Chapter 24).")
        thinking_steps.append("Structuring 12-month or 24-month roadmap with quarterly milestones and contingency buffers.")

        reply = """### 📅 BT301 Timeline & Gantt Chart Guide (Chapter 24)

Reviewers look for an achievable, logically sequenced schedule with explicit milestones and buffer time for experimental troubleshooting.

---

### 🗺️ Standard 12-Month Project Architecture:
• **Months 1–3 (Q1): Chassis Preparation & Vector Construction:**  
  *Milestone 1:* Sequence-verified recombinant construct generated and transformed into host chassis.
• **Months 4–6 (Q2): Expression Optimization & Pilot Screen:**  
  *Milestone 2:* Target molecule expressed with confirmed yield > 50 mg/L or detectable enzymatic activity.
• **Months 7–9 (Q3): Full Analytical Characterization & Controls:**  
  *Milestone 3:* Triplicate assays completed across all positive reference standards and negative matrix blanks.
• **Months 10–12 (Q4): Validation Replicates, Data Synthesis & Defense:**  
  *Milestone 4:* Final statistical analysis (ANOVA, 95% CI) and publication manuscript drafted.

---

### 🛡️ Mandatory Contingency Buffer (Chapter 24 §24.4):
Reserve the final 2 months exclusively for data analysis and buffer time. Never schedule critical laboratory bench experiments into the final month before graduation or submission."""

        actions = [
            {"label": "Open Chapter 24: Timeline & Gantt", "icon": "📅", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(24);"},
            {"label": "Build My Gantt Schedule", "icon": "📊", "onClickJs": "quickSendCopilotPrompt('help me structure my 12 month Gantt chart')"}
        ]
        suggestions = [
            {"text": "📅 How to define quarterly milestones?", "prompt": "how to define quarterly milestones for my proposal"},
            {"text": "🛡️ How to calculate technical benchmarks?", "prompt": "how to establish quantitative benchmarks for proposal milestones"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "timeline_formulation"
        }

    # BT301 ROUTE: Experimental Controls & Replicates Coach (Chapter 23)
    elif is_controls_coach:
        thinking_steps.append("Identified Experimental Controls & Replicates Inquiry (BT301 Guide • Chapter 23).")
        thinking_steps.append("Enforcing the 4 mandatory control groups and biological vs. technical replicate standards.")

        reply = r"""### 🧪 BT301 Experimental Controls & Rigor Guide (Chapter 23)

Reviewer 2 frequently writes: *"The proposed methodology lacks rigorous controls."* In biotechnology, you must deploy the **4 Non-Negotiable Experimental Controls**:

---

### 🛡️ The 4 Mandatory Experimental Controls:
1. **Negative Control (Baseline Specificity):**  
   Non-targeting gRNA (CRISPR), empty plasmid vector, or untreated host cells. Proves signal is not due to vector or cellular background.
2. **Positive Reference Standard (Assay Validity):**  
   Commercially validated benchmark (e.g. wild-type enzyme, FDA-approved therapeutic, or synthetic target DNA). Proves your assay chemistry functions under tested conditions.
3. **Matrix-Matched Blank (Interference Check):**  
   Authentic patient serum, uninoculated plant sap, or sterile soil without target analyte. Proves matrix components (e.g. humic acids, endogenous proteases) do not cause false positives.
4. **Vehicle / Sham Control (Solvent Effect):**  
   Buffer with identical DMSO, glycerol, or ethanol concentration without bioactive compound. Proves observed bioactivity is not solvent toxicity.

---

### 🔬 Replicates Rule of Rigor:
• **Biological Replicates (n ≥ 3):** Independent cultures grown on different days or separate test subjects. Used for statistical significance (p < 0.05).
• **Technical Replicates (Triplicate):** Pipetting replicates from the same biological sample. Proves pipetting precision, not biological reproducibility."""

        actions = [
            {"label": "Open Chapter 23: Methodology", "icon": "🧪", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(23);"},
            {"label": "Audit Controls for My Project", "icon": "🔍", "onClickJs": "quickSendCopilotPrompt('what controls do I need for my active proposal')"}
        ]
        suggestions = [
            {"text": "🧪 What negative control for CRISPR?", "prompt": "what negative control should I use for CRISPR diagnostics?"},
            {"text": "📊 How many replicates do I need?", "prompt": "difference between biological and technical replicates in grant proposals"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "controls_formulation"
        }

    # BT301 ROUTE: Statistical Rigor & Limit of Detection (Chapter 2 & 23)
    elif is_stats_coach:
        thinking_steps.append("Identified Statistical Rigor & Limit of Detection Inquiry (BT301 Guide • Chapter 2 & 23).")
        thinking_steps.append("Formulating IUPAC/CLSI limit of detection equations and hypothesis testing decision trees.")

        reply = r"""### 📊 BT301 Statistical Rigor & Limit of Detection (LoD) Guide

Statistical rigor distinguishes an undergraduate lab report from a fundable research proposal.

---

### 📐 Standard IUPAC / CLSI Limit of Detection (LoD) Equation:
**LoD (Limit of Detection)** = Mean(Blank) + 3.3 × SD(Blank)
**LoQ (Limit of Quantitation)** = Mean(Blank) + 10 × SD(Blank)
• Mean(Blank): Mean signal of matrix-matched blank (n ≥ 20 replicates).
• SD(Blank): Standard deviation of matrix-matched blank.

For binary diagnostics (positive/negative), use **Probit Regression Analysis** to identify the concentration that yields 95% positive detection with 95% Confidence Intervals.

---

### 📈 Statistical Test Decision Matrix (Chapter 2 §2.2):
• **2 Groups (e.g. Treated vs. Untreated):** Two-tailed Student's t-test (paired if same subject before/after; unpaired otherwise).
• **≥ 3 Groups with 1 Factor:** One-Way ANOVA followed by **Tukey's Post-Hoc HSD** (compares all pairs) or **Dunnett's test** (compares all to control).
• **2 Factors (e.g. Dose × Time):** Two-Way ANOVA with **Bonferroni correction** for multiple comparisons.
• **Threshold:** Set α = 0.05. Report exact p-values (e.g. p = 0.018), never just p < 0.05."""

        actions = [
            {"label": "Open Chapter 2: Statistics", "icon": "📊", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(2);"},
            {"label": "Open Chapter 23: Methodology", "icon": "🧪", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(23);"}
        ]
        suggestions = [
            {"text": "📊 How to choose between t-test and ANOVA?", "prompt": "when to use ANOVA vs t-test in biotechnology proposals"},
            {"text": "🎯 How to calculate sample size?", "prompt": "how to perform power calculation for sample size"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "statistics_rigor"
        }

    # BT301 ROUTE: Reviewer 2 Mock Defense / Faculty Cross-Examination ("Grill Me")
    elif is_grilling:
        thinking_steps.append("Activating Reviewer 2 Mock Defense & Faculty Cross-Examination Simulator.")
        thinking_steps.append(f"Targeting active proposal: Title='{live_title or 'Untitled'}', Chassis='{live_chassis or 'Unspecified'}', Tool='{live_tool or 'Unspecified'}'.")
        thinking_steps.append("Formulating 4 critical reviewer cross-examination questions.")

        reply = f"""### 🧠 Reviewer 2 Faculty Defense Station: Cross-Examination
**Active Proposal:** *"{live_title or "Your Research Draft"}"*

I am acting as **Reviewer 2** on your faculty grant evaluation panel. Here are the 4 hardest questions your committee will ask during your viva defense:

---

### ⚔️ Question 1: The Feasibility & Expression Trap
*"{live_chassis or 'Your chosen host'} is notorious for forming insoluble inclusion bodies when overexpressing foreign recombinant proteins. How will you confirm soluble expression before spending your budget on downstream characterization?"*

### ⚔️ Question 2: The Benchmark & Sensitivity Challenge
*"Existing commercial assays already detect {live_target or 'the target'} reliably. What is your quantitative benchmark (LoD or kcat/Km), and why would a clinic or industrial partner adopt your method over established gold standards?"*

### ⚔️ Question 3: The Decoupling Vulnerability
*"If Aim 1 produces an expression yield below your threshold (< 50 mg/L), how do you adapt your work package? Have you established clear milestone acceptance criteria?"*

### ⚔️ Question 4: Matrix Interference & Specificity
*"Have you validated that non-target homologous molecules or clinical matrix components will not cause false-positive signal in your standardized assay?"*

---

💡 **How would you defend against Question 1 or Question 3?** Type your response, and I will critique your defense!"""

        actions = [
            {"label": "Show Model Defense for Q1", "icon": "🛡️", "onClickJs": "quickSendCopilotPrompt('model defense for Question 1 inclusion bodies')"},
            {"label": "Show Model Defense for Q3", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('model defense for Question 3 decoupled aims')"}
        ]
        suggestions = [
            {"text": "🛡️ Model defense for Question 1", "prompt": "how to defend against protein expression failure in viva"},
            {"text": "🎯 How to answer Question 3", "prompt": "how to defend decoupled aims in oral defense"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "reviewer_defense"
        }

    # BT301 ROUTE: Mechanistic Hypothesis Formulation (Chapter 9 & 13)
    elif is_hypothesis_coach:
        thinking_steps.append("Identified Mechanistic Hypothesis Formulation Inquiry (BT301 Guide — Chapter 9 & 13).")
        thinking_steps.append("Applying standard 4-pillar hypothesis structure with quantitative success benchmark.")

        reply = """### 🧬 BT301 Mechanistic Hypothesis Formulation (Chapter 9)

In BT301 grant evaluation, a hypothesis is **not a wild guess** and **not a descriptive statement**. It is a **mechanistic, testable prediction** grounded in published biochemistry.

---

### 🧩 The Mechanistic Hypothesis Blueprint:
**Mechanistic Hypothesis Formula:** We hypothesize that [Active Agent / Construct] will [Action Verb] [Molecular Target] by [Biochemical Mechanism], thereby [Quantified Benchmark] in [Host Chassis / Model Matrix].

---

### ⚖️ Descriptive vs. Mechanistic Hypothesis:
• ❌ **Descriptive (School-Lab Trap):**  
  *“We hypothesize that plant extract X will have an effect on bacteria.”*  
  *(Why reviewers reject it: No active agent, no biochemical mechanism, no target molecule, no quantitative threshold.)*

• ✅ **Mechanistic & Fundable:**  
  *“We hypothesize that an ethosomal nano-emulsion of Calendula officinalis will accelerate dermal wound re-epithelialization by downregulating pro-inflammatory TNF-alpha and IL-6 expression in human epidermal keratinocytes, achieving >75% wound closure within 48 hours.”*

---

### 🎯 3 Golden Criteria of a Fundable Hypothesis (Criterion 2):
1. **Directionality:** Does it state an increase, decrease, inhibition, or acceleration?
2. **Biochemical Mechanism:** Does it specify *how* (pathway, receptor, domain, enzyme)?
3. **Falsifiability:** Can a negative control or statistical test (p < 0.05) prove it wrong?

---

💡 **Let's construct your hypothesis together!** What is your active tool/agent and target molecule?"""

        actions = [
            {"label": "📖 Open Chapter 9: Research Funnel", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(9);"},
            {"label": "📖 Open Chapter 13: Building a Sentence", "icon": "✍️", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(13);"},
            {"label": "🎯 Draft 3 Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us draft 3 decoupled specific aims')"}
        ]

        suggestions = [
            {"text": "✍️ Refine my current hypothesis", "prompt": "here is my hypothesis: can you critique and refine it?"},
            {"text": "🔍 Help me write a gap sentence", "prompt": "how to write a literature gap sentence"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_hypothesis_coaching"
        }

    # BT301 ROUTE: Literature Gap Statement (Chapter 8 & 21)
    elif is_gap_coach:
        thinking_steps.append("Identified Literature Gap Statement Inquiry (BT301 Guide — Chapter 8 & 21).")
        thinking_steps.append("Deconstructing gap taxonomy and contrastive pivot structures.")

        reply = """### 🔍 BT301 Literature Gap Formulation (Chapter 8 & 21)

A literature gap is **not** simply saying *“no one has studied this before.”* A genuine research gap is a specific, high-value problem that prior scientific efforts failed to resolve or overlooked.

---

### 🧩 The 3-Part Literature Gap Pivot Formula:
**Literature Gap Blueprint:** [Acknowledge Established Prior Work] + [However / Despite] + [Unresolved Mechanistic Void].

• **Worked Example:**  
  *“Although numerous studies demonstrated the broad-spectrum antibacterial efficacy of silver nanoparticles in vitro, their clinical topical application remains severely constrained by cellular cytotoxicity and rapid oxidation in aqueous formulations.”*

---

### 📚 The 4 Valid Gap Archetypes (Chapter 8):
1. **Methodological Gap:** Existing assays are too slow, expensive, or insensitive (e.g. 72-hour culture vs. 15-minute isothermal amplification).
2. **Mechanistic Gap:** The clinical effect is known, but the exact cellular pathway or receptor remains uncharacterized.
3. **Formulation / Delivery Gap:** The bioactive compound degrades rapidly or fails to cross biological barriers (e.g. stratum corneum).
4. **Chassis / Environmental Gap:** A molecular system works in laboratory buffer but fails in authentic clinical or industrial matrices (e.g. humic acid inhibition).

---

💡 **Let's draft your literature gap sentence!** Share what prior studies found and what specific bottleneck your project solves."""

        actions = [
            {"label": "📖 Open Chapter 8: Finding the Gap", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(8);"},
            {"label": "📖 Open Chapter 21: State of the Art", "icon": "📑", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(21);"},
            {"label": "✍️ Formulate Hypothesis Next", "icon": "🧬", "onClickJs": "quickSendCopilotPrompt('how to write a mechanistic hypothesis sentence')"}
        ]

        suggestions = [
            {"text": "🔍 Critique my literature gap", "prompt": "here is my gap statement: can you critique it?"},
            {"text": "✍️ Guide me to write a sentence", "prompt": "can you help me and guide on how to formulate a sentence"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_gap_coaching"
        }

    # BT301 ROUTE: Sentence Formulation & Scientific Writing (Chapter 13)
    elif is_sentence_coach:
        thinking_steps.append("Identified Scientific Sentence Formulation Inquiry (BT301 Guide — Chapter 13: Building a Sentence).")
        thinking_steps.append("Applying 4-part scientific architecture: Subject (Agent/Tool) + Verb (Precise Action) + Object (Measured Property) + Condition (Matrix/Model).")
        thinking_steps.append("Synthesizing actionable archetypes, verb matrices, and section tense guidelines.")

        reply = """### ✍️ BT301 Scientific Sentence Formulation Guide (Chapter 13)

Academic proposals require **active, mechanistic, and quantified** sentences. Reviewers look for clear agency: who or what is acting, what precise biophysical action is occurring, and under what exact conditions.

---

### 🧩 1. The Universal 4-Part Scientific Sentence Formula:
**Sentence Blueprint:** [Subject / Agent] + [Active Action Verb] + [Direct Object / Measured Endpoint] + [Condition / Chassis]

• **Example:**  
  *“The ethanolic Calendula officinalis extract **(Subject)** inhibited **(Verb)** biofilm formation **(Object)** in cultured Methicillin-resistant Staphylococcus aureus **(Condition)**.”*

---

### 📐 2. The 5 Essential Sentence Types in a Research Proposal:

| Section | Sentence Archetype | Formula & Worked Example |
| :--- | :--- | :--- |
| **Sec 2: Problem** | **The Real-World Bottleneck** | *"[Disease / Contaminant] causes [quantified cost / mortality], yet current standard [methods] suffer from [specific technical limitation]."*<br>*(e.g., "Sepsis claims over 11 million lives annually, yet blood-culture confirmation requires 48–72 hours to return antibiotic resistance profiles.")* |
| **Sec 2: Gap Pivot** | **The Unresolved Void** | *"Although previous studies established that [known fact], whether [key variable] can [target effect] under [relevant condition] remains uncharacterized."*<br>*(e.g., "Although recombinant PETase degrades amorphous PET at 30°C, its rapid thermal inactivation at >50°C prevents commercial industrial deployment.")* |
| **Sec 3: Hypothesis** | **The Mechanistic Prediction** | *"We hypothesize that [Agent / Construct] will [action verb] [target] by [biochemical mechanism], achieving [quantified milestone] in [model chassis]."*<br>*(e.g., "We hypothesize that disulfide-stabilized PETase variants will resist thermal unfolding at 65°C by decreasing backbone entropy, depolymerizing >85% post-consumer PET within 12 hours.")* |
| **Sec 3: Objective** | **The Measurable Aim** | *"To [action verb: quantify / optimize / express / evaluate] [parameter] using [method / assay] in order to [milestone benchmark]."*<br>*(e.g., "To evaluate kinetic catalytic turnover (kcat / Km) of five engineered variants across 40–70°C using spectrophotometric esterase assays.")* |
| **Sec 4: Protocol** | **Future-Tense Active Procedure** | *"[Sample / Formulation] will be [passive action verb] at [operating condition] for [duration] with [positive & negative controls] to [endpoint readout]."*<br>*(e.g., "Triplicate 50 mg substrate samples will be incubated at 65°C in 50 mM glycine-NaOH buffer (pH 9.0) with wild-type and heat-inactivated enzyme controls.")* |

---

### 🔬 3. Scientific Verb Choice Matrix:
• **Define / Specify:** *is defined as, refers to, comprises, encompasses*  
• **Describe Biochemical Mechanism:** *catalyzes, mediates, regulates, downregulates, upregulates, transcribes, cleaves*  
• **Report Literature:** *demonstrated, observed, established, confirmed, identified*  
• **Cautious Hedging:** *suggests, indicates, supports the hypothesis that, is consistent with* *(never use 'proves' in biology)*  
• **Quantify Effect:** *inhibited by 68%, accelerated by 3.2-fold, reduced below detection threshold*

---

### 💡 Informal → Academic Quick Conversions:
• *"A lot of studies"* ➔ **"Numerous empirical investigations"**  
• *"Scientists found out that"* ➔ **"Researchers previously demonstrated that"**  
• *"This proves that"* ➔ **"These findings provide strong evidence that"**  
• *"We wanted to see if"* ➔ **"This investigation aims to determine whether"**  
• *"The extract did not work"* ➔ **"The formulation exhibited no statistically significant inhibition (p > 0.05)"**

---

🎯 **What sentence would you like to draft right now?** Select an archetype below or share your draft sentence and we will refine it together!"""

        actions = [
            {"label": "📖 Open Chapter 13: Building a Sentence", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(13);"},
            {"label": "✍️ Formulate Hypothesis Sentence", "icon": "🧬", "onClickJs": "quickSendCopilotPrompt('how to write a mechanistic hypothesis sentence')"},
            {"label": "🔍 Formulate Literature Gap Sentence", "icon": "🔍", "onClickJs": "quickSendCopilotPrompt('how to write a literature gap sentence')"},
            {"label": "🎯 Formulate Specific Aim Sentence", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('how to write a specific aim sentence')"},
            {"label": "📋 View Master Pre-Submission Checklist", "icon": "✅", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(28);"}
        ]

        suggestions = [
            {"text": "✍️ Help me write my hypothesis sentence", "prompt": "help me write a mechanistic hypothesis sentence for my proposal"},
            {"text": "🔍 Help me write a gap pivot sentence", "prompt": "help me write a literature gap pivot sentence"},
            {"text": "📖 Browse all 31 Guide chapters", "prompt": "show me the bt301 course guide"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_sentence_coaching"
        }

    # BT301 ROUTE: APA 7th Edition Citation & Reference Coaching (Chapter 5)
    elif is_citation_coach:
        thinking_steps.append("Identified Academic Citation & Reference Guidance Request (BT301 Guide — Chapter 5 §5.2).")
        thinking_steps.append("Retrieving APA Style (7th Edition) rules: matching rule (§5.2.1), in-text formats (§5.2.2), reference list mechanics (§5.2.3), source templates A–K (§5.2.4), and common pitfalls (§5.2.6).")

        # Check for specific inquiry types
        is_audit = bool(re.search(r'(https?://|doi\.org|\b10\.\d{4,}|vol\b|pp\.|issue|\b(19|20)\d{2}\b)', text)) and bool(re.search(r'(check|audit|correct|format|review|is this|rate)', lower))
        is_et_al = bool(re.search(r'\b(et\s+al|how\s+many\s+authors|author\s+count|three\s+authors|two\s+authors|one\s+author)\b', lower))
        is_template_req = bool(re.search(r'\b(preprint|biorxiv|medrxiv|arxiv|book|chapter|report|website|webpage|thesis|dissertation|conference|dataset|software|patent|template|templates)\b', lower))
        is_mistakes = bool(re.search(r'\b(mistake|mistakes|error|errors|pitfall|pitfalls|common\s+apa)\b', lower))
        is_manager = bool(re.search(r'\b(zotero|mendeley|reference\s+manager|manager|workflow)\b', lower))
        is_vancouver = bool(re.search(r'\b(vancouver|numerical|superscript)\b', lower))

        if is_audit:
            thinking_steps.append("Performing algorithmic audit on student-provided citation draft.")
            audit_findings = []
            
            # Sentence case check
            title_case_match = re.search(r'(?:[A-Z][a-z]+\s+){3,}(?:in|of|and|for|with|by)\s+(?:[A-Z][a-z]+\s+){2,}', text)
            if title_case_match:
                audit_findings.append("⚠️ **Title Capitalization:** Article titles must use **sentence case** (capitalize only the first word, first word after colon, and proper nouns/genus names like *Calendula*). Journal titles, however, remain in Title Case and italics.")
            
            # DOI checks
            if "doi:" in text.lower():
                audit_findings.append("⚠️ **DOI Format:** Present DOIs as direct hyperlinks `https://doi.org/10.xxxx/...`. Do not write `doi:` before the link.")
            if re.search(r'https?://doi\.org/[^\s]+\.\s*$', text.strip()):
                audit_findings.append("⚠️ **Trailing Period on DOI:** Do NOT place a period after the DOI URL (`https://doi.org/...`). A trailing period breaks the web link when clicked by reviewers.")
            
            # Retrieved from check
            if "retrieved from" in text.lower():
                audit_findings.append("⚠️ **Deprecated 'Retrieved from':** APA 7th eliminated 'Retrieved from' for journal articles with DOIs. State the DOI URL directly.")
                
            # Ampersand vs and check
            if re.search(r'[A-Za-z]+,\s*[A-Z]\.?\s*and\s+[A-Za-z]+,\s*[A-Z]\.?', text):
                audit_findings.append("⚠️ **Ampersand in Author List:** Use an ampersand (`&`) before the final author in the reference list, not the word 'and' (e.g. `Khan, M. A., & Rahman, S. L.`).")
            
            # et al syntax check
            if "et. al" in text.lower():
                audit_findings.append("⚠️ **Latin Syntax:** Write `et al.` (no period after 'et'). 'Et' is a complete Latin word meaning 'and'; 'al.' is an abbreviation for *alia* and requires a trailing period.")

            if audit_findings:
                audit_summary = "\n".join(audit_findings)
            else:
                audit_summary = "✓ **Syntax Audit Passed:** Your draft shows solid alignment with core APA 7th Edition conventions (author format, date placement, and clean DOI presentation)."

            reply = f"""### 📚 APA 7th Edition Citation Audit (Chapter 5 §5.2)

{audit_summary}

---

### 🧩 Standard Journal Article Template (Source Type A):
**APA 7th Reference Format:** Author, A. A., & Author, B. B. (Year). Title of article in sentence case. *Journal Title in Italics*, *volume*(issue), pp–pp. https://doi.org/xxxxx

• **Canonical Example (Real Paper):**  
  *Livak, K. J., & Schmittgen, T. D. (2001). Analysis of relative gene expression data using real-time quantitative PCR and the 2^(-ΔΔCT) method. Methods, 25(4), 402–408. https://doi.org/10.1006/meth.2001.1262*

---

### 💡 Core Rule Reminders from §5.2:
1. **The Matching Rule (§5.2.1):** Every in-text citation must appear in your reference list, and every reference entry must be cited in the text. One without the other is an automatic grading deduction.
2. **Hanging Indent (§5.2.3):** Reference list entries must have a hanging indent (first line flush left, subsequent lines indented 0.5 in / 1.27 cm).
3. **Alphabetical Order (§5.2.3):** Sort by the first author's surname from A to Z, not in order of appearance."""

        elif is_et_al:
            thinking_steps.append("Synthesizing APA 7th author count and et al. rules (§5.2.2).")
            reply = """### 👥 APA 7th Edition In-Text Author Count Rules (§5.2.2)

In APA 7th Edition, in-text citations follow clear author-count rules. Note that **3 or more authors use *et al.* from the very first citation**:

| Authors on Source | Parenthetical Citation (Inside brackets) | Narrative Citation (In your prose) | Format Rule |
| :--- | :--- | :--- | :--- |
| **One author** | `(Khan, 2022)` | `Khan (2022)` | Always name the single author. |
| **Two authors** | `(Rahman & Lopez, 2023)` | `Rahman and Lopez (2023)` | Name both every time. Use **`&`** inside parentheses; spell out **`and`** in narrative prose. |
| **Three or more authors** | `(Chen et al., 2021)` | `Chen et al. (2021)` | **Shorten to first author + *et al.* from the very first citation!** (Period after *al.*, never after *et*). |
| **Group / Organization (1st use)** | `(World Health Organization [WHO], 2022)` | `World Health Organization (WHO, 2022)` | Introduce abbreviation in brackets. |
| **Group / Organization (later uses)** | `(WHO, 2022)` | `WHO (2022)` | Use acronym alone. |
| **No publication date** | `(Khan, n.d.)` | `Khan (n.d.)` | Use `n.d.` for "no date". |
| **Two authors, same surname** | `(A. Khan, 2020; M. Khan, 2021)` | `A. Khan (2020)` | Add first initials to prevent ambiguity. |

---

### 📌 Special In-Text Scenarios:
• **Multiple sources in one parenthesis:** Sort alphabetically by first author's surname, separated by semicolons:  
  *(Chen et al., 2021; Khan, 2022; Rahman & Lopez, 2023)*
• **Same author, same year:** Add lowercase letters alphabetically by article title:  
  *(Khan, 2022a, 2022b)*
• **Specific page or table:** Add locator: `(Khan, 2022, p. 45)` or `(Khan, 2022, Table 2)`.
• **Secondary source (found inside another paper):** Cite primary in text, credit secondary:  
  *(O'Connor, 1998, as cited in Chen et al., 2021)* — *Only Chen et al. goes in your reference list.*"""

        elif is_template_req:
            thinking_steps.append("Synthesizing 11 Source Type Reference Templates (§5.2.4 A–K).")
            reply = """### 📋 APA 7th Edition Reference Formats by Source Type (§5.2.4)

Here are the exact templates and examples for the sources you use in biotechnology proposals:

#### A. Journal Article with DOI (Standard)
• **Template:** `Author, A. A., & Author, B. B. (Year). Title of article in sentence case. Journal Title in Italics, volume(issue), pp–pp. https://doi.org/xxxxx`  
• **Example (Real Paper):**  
  *Livak, K. J., & Schmittgen, T. D. (2001). Analysis of relative gene expression data using real-time quantitative PCR and the 2^(-ΔΔCT) method. Methods, 25(4), 402–408. https://doi.org/10.1006/meth.2001.1262*

#### B. Journal Article with 21+ Authors
• List the first 19 authors, insert an ellipsis (`...`), then add the final author's name (no ampersand).

#### D. Preprint (bioRxiv, medRxiv, arXiv, Research Square)
• **Template:** `Author, A. A. (Year). Title of preprint in sentence case. Repository Name in Italics. https://doi.org/xxxxx`  
• **Example:**  
  *Ghoneim, M. A., & Hassan, S. K. (2024). Optimized topical delivery of Calendula flavonoids via lipid nanoparticles. bioRxiv. https://doi.org/10.1101/2024.03.15.585123*

#### E. Entire Book
• **Template:** `Author, A. A. (Year). Title of book in sentence case and italics (edition). Publisher.`  
• **Example:**  
  *Sambrook, J., & Russell, D. W. (2001). Molecular cloning: A laboratory manual (3rd ed.). Cold Spring Harbor Laboratory Press.*

#### F. Chapter in an Edited Book
• **Template:** `Author, A. A. (Year). Title of chapter in sentence case. In E. E. Editor (Ed.), Title of book in italics (pp. xx–xx). Publisher.`

#### G. Report by Government or Organization
• **Template:** `World Health Organization. (Year). Title of report in italics (Report No. xxx). URL`

#### H. Web Page on a Website
• **Template:** `Author or Organization. (Year, Month Day). Title of page in italics. Website Name. URL`

#### I. Master's Thesis or Doctoral Dissertation
• **Template:** `Author, A. A. (Year). Title in sentence case and italics [Master's thesis / Doctoral dissertation, University Name]. Database Name.`

#### K. Software or Dataset
• **Template:** `Developer, D. D. / Organization. (Year). Title of software (Version x.x) [Computer software / Data set]. Publisher or URL.`  
• **Example:**  
  *R Core Team. (2023). R: A language and environment for statistical computing (Version 4.3.1) [Computer software]. R Foundation for Statistical Computing. https://www.R-project.org/*

#### Patent
• **Template:** `Inventor, I. I. (Year). Title of patent in sentence case (Patent No. xxxxx). Patent Office.`"""

        elif is_mistakes:
            thinking_steps.append("Synthesizing Common APA Mistakes Table (§5.2.6).")
            reply = """### ⚠️ 10 Common APA Mistakes and How to Avoid Them (§5.2.6)

Academic reviewers and faculty audit references rigorously. Here are the 10 most frequent mistakes and their immediate fixes:

| # | What Students Do Wrong | Why It Is Wrong | What to Do Instead (Correct APA 7th) |
| :--- | :--- | :--- | :--- |
| **1** | Capitalizing Every Word In The Article Title | APA 7th uses **sentence case** for article titles. | Capitalize **only** the first word, first word after colon, and proper nouns/genus names. *(e.g. "Formulation of cream...")* |
| **2** | Writing `(Chen et. al, 2021)` | "Et" is a whole word (meaning "and"); it has no period. "Al." is an abbreviation and takes a period. | Write `(Chen et al., 2021)` — period after al, never after et. |
| **3** | Writing `(Rahman and Lopez, 2023)` inside parentheses | APA requires `&` inside parentheses; spell out `and` only in narrative prose outside brackets. | `(Rahman & Lopez, 2023)` in parentheses;<br>`Rahman and Lopez (2023)` in narrative. |
| **4** | Writing `(Rahman et al., 2023)` for two authors | *Et al.* is only for 3 or more authors. A two-author paper always names both authors. | Write `(Rahman & Lopez, 2023)` every single time. |
| **5** | Writing `doi:10.1016/...` | Older APA editions used `doi:`. APA 7th mandates live URL hyperlinks. | Write `https://doi.org/10.1016/...` |
| **6** | Putting a period after the DOI URL | The period becomes part of the web address and breaks the link when clicked. | End the reference entry with the bare DOI hyperlink. No final period. |
| **7** | Omitting the issue number when journals paginate by issue | Readers cannot locate the article if pagination restarts at page 1 each issue. | Include issue number in parentheses after volume: `Journal of Biotech, 12(3), 45–52.` |
| **8** | Alphabetizing by order of appearance | That is Vancouver style, not APA. APA reference lists are strictly alphabetical by first author surname. | Sort the reference list alphabetically from A to Z by first author's last name. |
| **9** | Writing `Retrieved from http://...` | APA 7th eliminated "Retrieved from" for standard online journal articles and preprints. | Provide the bare URL or DOI directly without preamble. |
| **10** | Citing in text but omitting from reference list (or vice versa) | **The Matching Rule (§5.2.1):** Every in-text citation must have a reference list entry, and every reference must be cited in text. | Cross-check before submitting: count in-text citations against reference entries. |"""

        elif is_manager:
            thinking_steps.append("Synthesizing Reference Manager Guidance (§5.2.7).")
            reply = """### 💻 Reference Managers: Zotero & Mendeley Workflow (§5.2.7)

Typing citations by hand is slow and error-prone. In BT301, we strongly recommend using a dedicated reference manager:

#### Recommended Free Tools:
1. **Zotero** (Highly Recommended): Free, open source, works seamlessly with Word, Google Docs, and LibreOffice.
2. **Mendeley**: Free, strong PDF annotation tools, Elsevier ecosystem integration.

---

### 🔄 The 4-Step Reference Manager Workflow:
1. **Collect as you search:** Install the browser connector. When you find a paper on PubMed, ScienceDirect, or bioRxiv, click the icon to import bibliographic metadata and PDF. *Always check that the DOI was captured.*
2. **Organize:** Create a dedicated collection folder for your proposal (e.g., `BT301_Research_Proposal`).
3. **Insert while drafting:** Use the Zotero/Mendeley plugin in Microsoft Word or Google Docs. Click **Add Citation**, search the author or keyword, and select. Set your citation style to **American Psychological Association 7th edition**.
4. **Generate & Audit:** Place cursor at the end of your document and click **Add Bibliography**. Before submitting, audit against the §5.2.6 common mistakes (check that article titles are in sentence case and DOIs have no trailing period)."""

        elif is_vancouver:
            thinking_steps.append("Synthesizing Vancouver vs APA Style Comparison (§5.2.8).")
            reply = """### 🔢 Vancouver Style vs. APA Style (§5.2.8)

While APA 7th Edition is the default style for BT301, some biomedical journals (e.g., *The Lancet*, *Nature*) and government grant portals use **Vancouver Style** (numbered citations).

| Dimension | APA Style (7th Edition) | Vancouver Style (Numerical) |
| :--- | :--- | :--- |
| **In-text format** | Author-date: `(Rahman & Lopez, 2023)` or `Chen et al. (2021)` | Numbers in brackets `[1]` or superscripts `¹` |
| **Reference list order** | **Alphabetical** by first author's surname | **Numerical** in order of first appearance in text |
| **Author count in-text** | 1–2 authors named; 3+ use *et al.* immediately | Number only — no author names required in text |
| **Primary domain** | Social sciences, biotechnology, biochemistry, psychology | Clinical medicine, pharmacology, general science (*Nature*) |

💡 **Course Rule:** Default to APA 7th Edition unless your instructor, rubric, or target RFP explicitly specifies Vancouver. Never mix the two within the same document!"""

        else:
            # Master Overview
            thinking_steps.append("Synthesizing APA 7th Edition Master Citation Architecture (§5.2).")
            reply = """### 📚 BT301 APA Style (7th Edition) Citation Handbook (Chapter 5 §5.2)

APA is the default citation style in biotechnology academic proposals. It ensures every factual assertion is attributed with precision and verifiable by peer reviewers.

---

### ⚖️ 1. The Two Parts & The Matching Rule (§5.2.1):
Every cited source appears **twice** in your proposal:
1. **In-text citation:** Inside your sentence — tells the reviewer *whose idea or finding this is*.
2. **Reference-list entry:** In the "References" section at the end — tells the reviewer *how to retrieve the source*.

> ⚠️ **The Matching Rule:** Every in-text citation must appear in the reference list, and every reference-list entry must be cited in the text. One without the other is an automatic grading penalty.

---

### ✍️ 2. In-Text Citations (§5.2.2):
• **Parenthetical:** `(Rahman & Lopez, 2023)` — Used when the scientific idea is the focus.  
• **Narrative:** `Rahman and Lopez (2023) demonstrated that...` — Used when comparing studies or highlighting the investigators.  
• **3+ Authors:** `(Chen et al., 2021)` — **Use *et al.* from the very first citation!** (Period after al, none after et).

---

### 📖 3. Reference List Mechanics (§5.2.3):
• **Layout:** Sorted **alphabetically** by first author's last name. Formatted with a **hanging indent** (0.5 in / 1.27 cm).  
• **The 4 Elements:** `Author(s). (Year). Title. Source & DOI.`  
• **Title Capitalization Rule:** Article and book titles use **sentence case** (capitalize only the first word, first word after colon, and proper nouns like *Calendula* or CRISPR). Journal titles use **Title Case and italics**.  
• **DOIs:** Direct hyperlinks `https://doi.org/10.xxxx/...` with **no trailing period** and no "Retrieved from" prefix.

---

### 🧪 Canonical Reference Example:
*Livak, K. J., & Schmittgen, T. D. (2001). Analysis of relative gene expression data using real-time quantitative PCR and the 2^(-ΔΔCT) method. Methods, 25(4), 402–408. https://doi.org/10.1006/meth.2001.1262*

What citation or reference would you like to format or audit right now? Paste your draft reference below and I will check it against APA 7th Edition rules!"""

        actions = [
            {"label": "📚 Open Chapter 5: APA 7th Guide", "icon": "📚", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(5);"},
            {"label": "📋 11 Source Templates (A–K)", "icon": "📋", "onClickJs": "quickSendCopilotPrompt('show me the 11 APA 7th reference templates from Chapter 5')"},
            {"label": "⚠️ Common APA Mistakes Table", "icon": "⚠️", "onClickJs": "quickSendCopilotPrompt('what are the common APA mistakes in Chapter 5')"},
            {"label": "👥 In-Text Citation Rules & Et Al.", "icon": "👥", "onClickJs": "quickSendCopilotPrompt('how to do in-text citations in APA 7th with et al')"},
            {"label": "💻 Reference Manager Workflow", "icon": "💻", "onClickJs": "quickSendCopilotPrompt('how to use Zotero or Mendeley for APA references')"}
        ]

        suggestions = [
            {"text": "📋 Show 11 source type templates", "prompt": "show me the 11 APA 7th reference templates from Chapter 5"},
            {"text": "⚠️ 10 Common APA mistakes table", "prompt": "what are the common APA mistakes in Chapter 5"},
            {"text": "👥 How to use et al in text", "prompt": "how to do in-text citations in APA 7th with et al"},
            {"text": "🔍 Check my reference draft", "prompt": "can you audit my citation draft in APA 7th"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_apa_citations"
        }

    # BT301 ROUTE: Course Guide Navigator & Chapter Lookup
    elif is_guide_direct:
        thinking_steps.append("Identified BT301 Complete Course Guide Navigation Query.")
        ch_match = re.search(r'chapter\s*(\d+)', lower)
        ch_num = int(ch_match.group(1)) if ch_match else None

        if ch_num and get_chapter:
            ch_data = get_chapter(ch_num)
            if ch_data:
                thinking_steps.append(f"Loaded Chapter {ch_num}: {ch_data.get('title')}.")
                preview = ch_data.get('content', '')[:1000]
                reply = f"""### 📖 BT301 Guide — Chapter {ch_num}: {ch_data.get('title')}
**Part:** {ch_data.get('part')} • **Scope:** {ch_data.get('word_count')} words

{preview}...

---

💡 *Click the button below to read the full chapter, copy fill-in templates, and view the worked example in the interactive reader!*"""
                actions = [
                    {"label": f"📖 Open Full Chapter {ch_num} in Reader", "icon": "📖", "onClickJs": f"if(window.openBt301Guide) window.openBt301Guide({ch_num});"},
                    {"label": "📋 Master Pre-Submission Checklist", "icon": "✅", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(28);"},
                    {"label": "📝 View Fill-in Templates", "icon": "📝", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(29);"}
                ]
                suggestions = [
                    {"text": f"✍️ Help me write sentences for Chapter {ch_num}", "prompt": "can you help me and guide on how to formulate a sentence"},
                    {"text": "📖 Browse all 31 chapters", "prompt": "show me all chapters of the bt301 guide"}
                ]
                return {
                    "reply": reply,
                    "actions": actions,
                    "suggestions": suggestions,
                    "thinking": thinking_steps,
                    "concept": "bt301_guide_navigation"
                }

        # General guide overview
        thinking_steps.append("Presenting BT301 Guide master workflow and 'I'm Stuck' quick finder.")
        # General guide overview
        thinking_steps.append("Presenting BT301 Guide master workflow and 'I'm Stuck' quick finder.")
        reply = """### 📖 BT301 Complete Course Guide
**From Zero to a Fundable Research Proposal (31 Chapters)**

The complete course guide is fully integrated into your workspace! It provides step-by-step guidance from essential biotechnology foundations to experimental design, statistics, itemized budgets (EGP), and master glossary definitions.

---

### 🗺️ The 5-Phase Master Curriculum:
• **Part A: Foundations (Ch 1–5):** Science principles, essential vocabulary, statistics (p-value, SD, SEM), paper reading, ethics & AI tools.
• **Part B: Finding & Shaping Your Project (Ch 6–11):** Biotechnology sectors, literature search strings, finding the gap, research funnel, fundability criteria, team roles.
• **Part C: Academic Writing Skills (Ch 12–18):** Sentence formulation (Ch 13), scientific verbs, tenses, active vs passive, MEAL paragraph building, transitions, self-editing.
• **Part D: Writing the Proposal (Ch 19–26):** Section-by-section drafting: Title & Summary, Background & Problem, Specific Aims, Methodology & Controls, Expected Outcomes & Benchmarks, Timeline & Gantt, Itemized Budget (EGP), Impact & Tech Transfer.
• **Part E: Review & Submit (Ch 27–28):** 3-pass revision audit (Ch 27), master pre-submission checklist (Ch 28).
• **Part F: Reference & Templates (Ch 29–31):** Fill-in proposal templates (Ch 29), master A–Z glossary (Ch 30), one-page cheat sheets (Ch 31).

---

### 🔍 Quick "I'm Stuck" Finder:
• *Confused about Aim vs. Objective vs. Hypothesis?* → **Chapter 9**
• *Need to formulate active, mechanistic sentences?* → **Chapter 13**
• *Need to define the literature gap pivot?* → **Chapter 8 & 21**
• *Looking up a term definition or standard formula?* → **Chapter 30 (Glossary)**
• *Need copy-paste fill-in templates?* → **Chapter 29**

Click below to open the complete interactive guide reader:"""

        actions = [
            {"label": "📖 Open BT301 Complete Guide Reader", "icon": "📖", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(1);"},
            {"label": "✍️ Open Chapter 13: Building a Sentence", "icon": "✍️", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(13);"},
            {"label": "📚 Chapter 30: Master Glossary (A–Z)", "icon": "📚", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(30);"},
            {"label": "💰 Chapter 25: Itemized Budget (EGP)", "icon": "💰", "onClickJs": "if(window.openBt301Guide) window.openBt301Guide(25);"}
        ]

        suggestions = [
            {"text": "✍️ How do I formulate a sentence?", "prompt": "can you help me and guide on how to formulate a sentence"},
            {"text": "🎯 How to write a hypothesis?", "prompt": "how to write a mechanistic hypothesis sentence"},
            {"text": "📑 How to write a literature gap?", "prompt": "how to write a literature gap sentence"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "bt301_guide_navigation"
        }

    elif is_weather:
        thinking_steps.append("Detected casual conversation: weather / everyday human inquiry.")
        thinking_steps.append("Responding warmly with natural personality (avoiding rigid bioengineering framing).")

        reply = """🌤️ **Haha, well, as an AI living inside your browser and server, I don't get to step outside to check the weather!**

Though if you're stuck in a lab with no windows or grinding late on your laptop, I definitely hope it's nice and pleasant outside! 😄

Did you want to take a quick mental breather, or are we ready to jump back into engineering and brainstorming your proposal?"""

        actions = [
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "Brainstorm 3 Fresh Ideas", "icon": "🧠", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"},
            {"label": "Review My 3 Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us review and refine our 3 specific aims')"},
            {"label": "Explore Gene Therapy", "icon": "🧬", "onClickJs": "quickSendCopilotPrompt('can we talk about gene therapy')"}
        ]
        suggestions = [
            {"text": "💡 How to beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"},
            {"text": "🎙️ Grill me on this proposal", "prompt": "grill me on this proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "casual_weather"
        }

    # CASUAL CASE 2: Personal Greeting / How Are You
    elif is_how_are_you:
        thinking_steps.append("Detected personal greeting and check-in.")
        reply = """😊 **I'm doing great, thank you for asking!**

I'm right here in your corner, ready to bounce around new project ideas, dive into the biochemistry, or help you polish whatever section you're working on.

How are things going on your end today? How is the proposal shaping up?"""

        actions = [
            {"label": "Brainstorm an Idea with Me", "icon": "🧠", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"},
            {"label": "Review My Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us review and refine our 3 specific aims')"},
            {"label": "Check Proposal Score", "icon": "📊", "onClickJs": "quickSendCopilotPrompt('how ready is my proposal?')"}
        ]
        suggestions = [
            {"text": "💡 Beat the Host-Swap Trap", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"},
            {"text": "🎙️ Simulate Reviewer 2", "prompt": "grill me on this proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "casual_checkin"
        }

    # CASUAL CASE 3: Fatigue / Coffee / Break Request
    elif is_fatigue and not is_food:
        thinking_steps.append("Detected student fatigue / break request.")
        reply = """☕ **Definitely step away for a minute and grab that coffee or take a quick walk!**

Crafting a publication-grade grant proposal takes serious mental focus. The enzymes, promoters, and assay controls will still be right here when you get back.

Take your time, and whenever you're refreshed and ready to jump back into the science, just say the word!"""

        actions = [
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "I'm Back, Let's Continue!", "icon": "🚀", "onClickJs": "quickSendCopilotPrompt('I am back, let us continue our proposal')"}
        ]
        suggestions = [
            {"text": "🎯 Review Specific Aims", "prompt": "Let us review and refine our 3 specific aims"},
            {"text": "✨ Auto-assemble blueprint", "prompt": "Auto-assemble complete proposal blueprint"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "casual_break"
        }

    # CASUAL CASE 4: Food, Meals & Nutrition (Daily Convo)
    elif is_food:
        thinking_steps.append("Detected daily conversation: food / meal recommendation.")
        thinking_steps.append("Formulating brain-boosting nutritional suggestions for academic focus.")
        reply = """🥗 **Here are a few quick, high-energy ideas to power your brain through study and research work:**

1. **Quick & Hearty (10–15 mins):**
   • **Mediterranean Power Bowl:** Warm brown rice or quinoa topped with hummus, crisp cucumbers, cherry tomatoes, olives, feta, and grilled chicken or spiced chickpeas with olive oil.
   • **Avocado & Egg Sourdough:** Toasted sourdough topped with smashed avocado, a sunny or poached egg, chili flakes, and sea salt. Delivers healthy fats and choline for sustained mental focus!

2. **Comforting & Warming:**
   • **Fast Veggie & Noodle Stir-Fry:** Quick-tossed noodles with broccoli, bell peppers, edamame or beef in a savory soy-garlic-sesame glaze.
   • **Hearty Soup & Crusty Bread:** Warm lentil soup, tomato bisque, or ramen with a soft-boiled egg and scallions.

3. **Brain-Fuel Snacks (No Sugar Crash):**
   • Greek yogurt with honey and blueberries (rich in polyphenols and slow-burning protein).
   • A handful of raw walnuts, almonds, and 85% dark chocolate.

💡 *What kind of food are you in the mood for right now—a quick comforting meal, or a light snack to keep working beside?*"""

        actions = [
            {"label": "Search Quick Recipes", "icon": "🌐", "onClickJs": "quickSendCopilotPrompt('search web for quick 15 minute healthy meal recipes')"},
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "Back to Proposal Work", "icon": "🔬", "onClickJs": "quickSendCopilotPrompt('Let us review and refine our 3 specific aims')"}
        ]
        suggestions = [
            {"text": "☕ Recommend good study snacks", "prompt": "what are the best brain foods for long study sessions?"},
            {"text": "🎯 Review Specific Aims", "prompt": "Let us review and refine our 3 specific aims"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "daily_food"
        }

    # CASUAL CASE 5: Stress, Sleep & Mental Wellness (Daily Convo)
    elif is_wellness:
        thinking_steps.append("Detected daily conversation: student stress / wellness reset.")
        reply = """🌿 **Take a slow, deep breath. Scientific writing and university deadlines can feel genuinely heavy, but you're doing great.**

When the brain is overloaded with protocols, citations, and data, cognitive fatigue is completely physiological. Here is a quick 3-step reset:

1. **The 4-4-4 Box Breathing Reset:**
   Inhale slowly through your nose for 4 seconds, hold for 4 seconds, exhale gently through your mouth for 4 seconds, and pause for 4 seconds. Doing this just 3 times immediately dials down cortisol and autonomic nervous arousal.

2. **Step Away From the Glass:**
   Look away from your screen for 5 minutes. Looking out a window at a distant horizon allows your eye ciliary muscles to relax, resetting dopaminergic focus.

3. **Break the Mountain into Pebbles:**
   You don't need to finish an entire grant proposal in one sitting. Pick just **one single sentence or aim** to draft, and let everything else wait until tomorrow. Sleep is when your brain actually consolidates biological insights!

💡 *Would you like to step away for a breather, hear a light lab joke, or just focus on one tiny paragraph together?*"""

        actions = [
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "Take a 5-Minute Break", "icon": "☕", "onClickJs": "quickSendCopilotPrompt('I am taking a quick coffee break')"},
            {"label": "Work on Just Aim 1", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us work on just Specific Aim 1')"}
        ]
        suggestions = [
            {"text": "🎵 Recommend study music", "prompt": "recommend chill music for scientific writing"},
            {"text": "💡 How to beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "daily_wellness"
        }

    # CASUAL CASE 6: Entertainment & Pop Culture (Movies, Books, Music)
    elif is_entertainment:
        thinking_steps.append("Detected daily conversation: entertainment / recommendations.")
        reply = """🎬 **Here are a few fantastic recommendations tailored for an inquisitive mind:**

### 🎥 Movies / Films:
• **Gattaca (1997):** The definitive genetic engineering and human destiny classic. Thought-provoking, stylish, and timeless.
• **Arrival (2016):** A breathtaking sci-fi masterpiece exploring linguistics, communication, and human perception of time.
• **Interstellar (2014):** Deep theoretical astrophysics, gravitational anomalies, and emotional human storytelling.

### 📚 Inspiring Books:
• **The Code Breaker** by Walter Isaacson (The gripping real-life chronicle of Jennifer Doudna and the CRISPR gene-editing revolution).
• **Project Hail Mary** by Andy Weir (Pure, joyful scientific problem-solving and microbiology under pressure).
• **The Emperor of All Maladies** by Siddhartha Mukherjee (A Pulitzer-winning biography of cellular biology and cancer).

### 🎵 Music for Writing & Deep Work:
• Lo-fi instrumental beats, ambient neoclassicism (Max Richter, Olafur Arnalds), or cinematic film scores (Hans Zimmer, Ludwig Göransson).

💡 *Are you looking for an intense film for movie night, an immersive book to unwind with, or background tunes while writing?*"""

        actions = [
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "Search Web for Details", "icon": "🌐", "onClickJs": f"quickSendCopilotPrompt('search web for {window_safe_escape(text[:25])}')"},
            {"label": "Back to Proposal Brainstorming", "icon": "🔬", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"}
        ]
        suggestions = [
            {"text": "🧬 Explore Gene Therapy", "prompt": "can we talk about gene therapy"},
            {"text": "💡 How to beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "daily_entertainment"
        }

    # CASUAL CASE 7: Motivation & Study Advice
    elif is_motivation:
        thinking_steps.append("Detected daily conversation: motivation / study advice.")
        reply = """⚡ **Here is a thought that always puts the scientific grind into perspective:**

Every major breakthrough—from Alexander Fleming discovering penicillin on a contaminated plate to Jennifer Doudna and Emmanuelle Charpentier discovering CRISPR—started with moments of confusion, failed experiments, and slow days.

You don't need to feel inspired or brilliant every hour. Scientific progress is simply **showing up, asking honest questions, and refining one hypothesis at a time**.

If you're feeling stuck or procrastinating, lower the bar: write just one sentence. Even a messy draft gives us something real to polish together!

💡 *What is the smallest step we can take right now? We can bounce around a fun idea, check a control, or just take five minutes to reset.*"""

        actions = [
            {"label": "Tell Me a Science Joke", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me a science joke')"},
            {"label": "Brainstorm 3 Fresh Ideas", "icon": "🧠", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"},
            {"label": "Review My 3 Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us review and refine our 3 specific aims')"}
        ]
        suggestions = [
            {"text": "☕ Take a quick break", "prompt": "I am taking a quick coffee break"},
            {"text": "🎙️ Simulate Reviewer 2", "prompt": "grill me on this proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "daily_motivation"
        }

    # CASUAL CASE 8: Science Jokes & Lighthearted Banter
    elif is_joke:
        thinking_steps.append("Detected request for science humor.")
        reply = """😄 **Here's a quick one from the lab:**

*Why are enzyme assays terrible at poker?*
Because they always reveal their active sites under pressure! 🃏

...Or: *Why did the E. coli cross the agar plate?*
To get to the other colony! 🧫

Whenever you're ready, we can dive back into serious molecular engineering!"""

        actions = [
            {"label": "Another Science Joke!", "icon": "😄", "onClickJs": "quickSendCopilotPrompt('tell me another science joke')"},
            {"label": "Back to Proposal Brainstorming", "icon": "🔬", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"}
        ]
        suggestions = [
            {"text": "🧬 Explore Gene Therapy", "prompt": "can we talk about gene therapy"},
            {"text": "🎙️ Grill me on this proposal", "prompt": "grill me on this proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "casual_joke"
        }

    # CASUAL CASE 9: AI Identity & Philosophy
    elif is_ai_q:
        thinking_steps.append("Detected AI identity / capability question.")
        reply = """🤖 **I am your Research Co-Pilot for BioWriter Studio!**

I don't have circadian rhythms, biological fatigue, or a physical body, but I am programmed with deep domain knowledge across molecular biology, gene editing, biocatalysis, and academic grant standards.

My purpose isn't to ghostwrite for you or talk like a rigid script — it's to think, brainstorm, and problem-solve alongside you as an inquisitive lab partner."""

        actions = [
            {"label": "Brainstorm an Idea with Me", "icon": "🧠", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"},
            {"label": "Review My 3 Specific Aims", "icon": "🎯", "onClickJs": "quickSendCopilotPrompt('Let us review and refine our 3 specific aims')"}
        ]
        suggestions = [
            {"text": "💡 How to beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"},
            {"text": "🎙️ Grill me on this proposal", "prompt": "grill me on this proposal"}
        ]
        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "ai_identity"
        }

    is_comparison = any(term in lower for term in ["instead of", "versus", " vs ", "should we use", "what if we switch", "compare", "comparison"])

    # CASE A: Comparative Trade-Off & Evaluation Dilemmas
    if is_comparison:
        thinking_steps.append("Detected comparative evaluation dilemma.")
        thinking_steps.append("Weighing expression feasibility, catalytic kinetics, and regulatory containment.")

        if ("aav" in lower and "lnp" in lower) or ("viral" in lower and "non-viral" in lower):
            reply = f"""⚖️ **Viral vs. Non-Viral Delivery: AAV vs. Targeted Lipid Nanoparticles (tLNPs):**

When evaluating delivery architectures for your active project *("{live_title or 'Active Proposal'}")*, grant committees focus on the trade-off between long-term expression and immunogenic safety:

| Parameter | **Adeno-Associated Virus (AAV)** | **Targeted Lipid Nanoparticles (tLNPs)** |
| :--- | :--- | :--- |
| **Cargo Type** | Single-stranded DNA (ssDNA) transgene | mRNA, Cas9-sgRNA RNP, or base editor mRNA |
| **Packaging Limit** | **Strict ceiling ~4.7 kb** between ITRs | High flexibility (>10 kb RNA payload) |
| **Expression Duration** | Episomal, long-term / permanent | Transient (hours to <24h), self-clearing |
| **Immunogenicity** | Pre-existing neutralizing antibodies block redosing | Low immunogenicity; fully repeatable systemic dosing |
| **Primary Tropism** | Serotype-dependent (AAV9 CNS/muscle, AAV8 liver) | Default liver accumulation; requires targeting ligands (e.g. anti-CD117) |
| **Manufacturing Cost** | Very high (complex viral vector purification & ultracentrifugation) | Scalable microfluidic mixing; lower lab reagent cost in EGP |
| **Best Proposal Fit** | In vivo monogenic gene replacement (*SMA, Hemophilia*) | Transient precision editing (*Base editing, mRNA vaccines*) |

---

💡 **Proposal Connection:** If your project involves CRISPR base/prime editing, **tLNPs are vastly preferred** because transient endonuclease expression (<24 hours) reduces off-target genomic cleavage and chromosomal translocations by >90% compared to permanent viral expression!"""
        elif ("e. coli" in lower or "ecoli" in lower or "bl21" in lower) and ("pichia" in lower or "pastoris" in lower or "yeast" in lower):
            reply = f"""⚖️ **Bacterial vs. Eukaryotic Host Chassis: E. coli vs. Pichia pastoris:**

When selecting your host chassis for recombinant enzyme expression in *("{live_title or 'Active Proposal'}")*:

| Feature | **Escherichia coli BL21(DE3)** | **Pichia pastoris (K. phaffii)** |
| :--- | :--- | :--- |
| **Organism Type** | Gram-negative bacterium (Prokaryote) | Methylotrophic budding yeast (Eukaryote) |
| **Expression Mode** | Intracellular cytoplasm / inclusion bodies | Extracellular secretion via α-mating factor |
| **Induction Mechanism** | IPTG derepression of lacUV5 / T7 promoter | Methanol induction of AOX1 promoter (>1000-fold) |
| **Post-Translational Mods**| None (reducing cytoplasm lacks disulfide bonds) | Core N-glycosylation (high mannose) & disulfide bonds |
| **Doubling Time** | **20–30 minutes** (rapid turnaround) | 90–120 minutes (high cell density >100 g/L DCW) |
| **Downstream Purification** | Cell lysis required; protease risk | Direct supernatant clarification; minimal host proteins |
| **Best Proposal Fit** | Fast screening, cytoplasmic biocatalysts | Secreted enzymes (*PETase, cutinases, antibodies*) |

---

💡 **Proposal Connection:** If your target enzyme contains complex structural disulfide bonds (such as the A180C–G165C bridge in DuraPETase), **Pichia pastoris** is superior because its endoplasmic reticulum carries native protein disulfide isomerases (PDIs) that guarantee proper oxidative folding!"""
        elif "base edit" in lower and "prime edit" in lower:
            reply = f"""⚖️ **Base Editing vs. Prime Editing: Precision Without Double-Strand Breaks:**

| Feature | **Base Editing (CBE / ABE)** | **Prime Editing (PE2 / PE5 / Twin-PE)** |
| :--- | :--- | :--- |
| **Mechanism** | Cas9 nickase fused to deaminase (TadA-8e / APOBEC1) | Cas9 nickase fused to engineered Reverse Transcriptase |
| **Guide RNA** | Standard single-guide RNA (sgRNA) | Prime Editing Guide RNA (pegRNA) with PBS & RTT |
| **Supported Edits** | 4 transition mutations: C→T, G→A, A→G, T→C | All 12 point transitions, plus insertions & deletions |
| **Double-Strand Breaks** | **Zero DSBs** | **Zero DSBs** |
| **Bystander Editing** | High if extra C or A in editing window (nt 4–8) | Minimal (templated strictly by reverse transcription) |
| **Packaging Footprint** | ~4.5 kb (fits inside single AAV capsid) | ~6.3 kb (requires dual split-intein AAV or LNP mRNA) |
| **Best Proposal Fit** | High-efficiency transitions (*Sickle cell BCL11A, PCSK9*) | Universal point corrections, micro-deletions (*DMD, CFTR*) |

---

💡 **Proposal Connection:** For monogenic transition mutations (like sickle cell or PCSK9), Base Editing offers unmatched efficiency (>70%). For insertions or non-transition mutations (like cystic fibrosis or DMD), Prime Editing provides total surgical precision!"""
        elif ("cas12" in lower or "detectr" in lower) and ("cas13" in lower or "sherlock" in lower):
            reply = f"""⚖️ **CRISPR-Cas12a (DETECTR) vs. CRISPR-Cas13a (SHERLOCK):**

| Parameter | **CRISPR-Cas12a (DETECTR / Cpf1)** | **CRISPR-Cas13a (SHERLOCK / C2c2)** |
| :--- | :--- | :--- |
| **Primary Target** | Double-stranded DNA (dsDNA) or ssDNA | Single-stranded RNA (ssRNA) |
| **PAM Requirement** | Strictly requires **5'-TTTV-3'** PAM (V = A/C/G) | No strict PAM; requires protospacer flanking site (PFS) |
| **Collateral Target** | Indiscriminate single-stranded DNase (**ssDNase**) | Indiscriminate single-stranded RNase (**ssRNase**) |
| **Catalytic Domain** | Single **RuvC** endodeoxyribonuclease domain | Dual **HEPN** endoribonuclease domains |
| **Optical Reporter** | Short fluorophore-quencher ssDNA (e.g. FAM-TTATT-BHQ1) | Fluorophore-quencher ssRNA (e.g. FAM-rUrUrUrUrU-BHQ1) |
| **Best Proposal Fit** | **Genomic DNA targets & AMR genes** (e.g. *mcr-1*, *blaKPC*, *NDM-1*) | **RNA viruses & mRNA transcription** (e.g. SARS-CoV-2, Ebola, gene expression) |

---

💡 **Proposal Connection:** For detecting plasmid-mediated resistance genes (*mcr-1*) in environmental wastewater, **Cas12a is the optimal choice** because plasmid DNA is double-stranded, eliminating the need for reverse transcriptase!"""
        else:
            reply = f"""⚖️ **Let's Think Through This Trade-Off Together:**

When deciding between alternative bioengineering approaches for your project, grant review panels evaluate three decisive factors:

1. **Biological Feasibility & Expression Burden:**
   Does the alternative host or vector introduce unneeded complexity (e.g. post-translational glycosylation mismatches, severe metabolic burden, or viral capsid packaging limits)?

2. **The Inventive Step & True Novelty:**
   Will shifting to this new tool solve an **explicit biophysical bottleneck** (e.g. higher thermostability Tm, faster kcat, or zero double-strand DNA breaks)? Or does it risk falling into the *"Host-Swap Trap"* (taking a well-characterized enzyme and simply cloning it into a new host without biological rationale)?

3. **Experimental Containment & Regulatory Pathway:**
   A cellular platform deployed in the wild requires strict synthetic biology kill-switches (auxotrophy, toxin-antitoxin *mazE/mazF*). An acellular or cell-free matrix bypasses living GMO release restrictions completely!

---

💡 **Recommendation:**
Tell me the two specific options you want to compare (for example: *AAV vs. Targeted LNPs*, or *E. coli vs. Pichia pastoris*), and I will generate an empirical side-by-side comparison table showing yield, kinetics, and feasibility!"""

        actions = [
            {"label": "Compare AAV vs. LNPs in Table", "icon": "📊", "onClickJs": "quickSendCopilotPrompt('compare AAV vs LNP in a table')"},
            {"label": "Compare E. coli vs. Pichia", "icon": "🧫", "onClickJs": "quickSendCopilotPrompt('compare E coli vs Pichia pastoris expression in a table')"},
            {"label": "Review Proposal Structure", "icon": "📋", "onClickJs": "quickSendCopilotPrompt('Let us review the structure of my active proposal')"}
        ]

        suggestions = [
            {"text": "💡 How to beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"},
            {"text": "🎙️ Simulate Reviewer 2 cross-examination", "prompt": "grill me on our host chassis and tool selection"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "concept": "comparative_tradeoff"
        }

    # CASE B: Technical Mechanism / Scientific Question (Matched Concept)
    elif matched_concept:
        c_title = matched_concept["category"]
        c_mech = matched_concept["mechanism"]
        c_params = matched_concept["lab_parameters"]
        c_pitfalls = matched_concept["key_pitfalls"]
        c_rescue = matched_concept["rescue_protocol"]
        c_bench = matched_concept["benchmark"]

        thinking_steps.append(f"Detected Task: Mechanistic & experimental protocol analysis ({c_title})")
        thinking_steps.append(f"Relevant Proposal Section: Sections 3 (Objectives), 4 (Methodology & Controls) & 5 (Expected Outcomes & Technical Benchmarks) — '{live_title or 'Active Proposal'}'")
        thinking_steps.append("Scientific Assumptions: Assumes standard purified buffer conditions; crude biological/environmental matrices require empirical titration.")
        thinking_steps.append("Evidence Status: [Curated Knowledge] — Distinguishes established biochemical principles from typical reported literature parameter ranges.")
        thinking_steps.append("Key Uncertainty: Host expression burden, matrix inhibition, and batch-to-batch kinetic variance must be empirically verified.")
        thinking_steps.append("Recommended Next Step: Verify Objective → Method → Control → Measurement → Expected Outcome alignment in Section 4.")

        thoughtful_openers = [
            f"That is a fundamental question in **{c_title}**. Let's think through what is actually happening at the molecular level:",
            f"Great inquiry. When review committees evaluate **{c_title}**, the central dilemma always comes down to the underlying biophysics. Here is how we break it down:",
            f"That touches right on the core engineering bottleneck of **{c_title}**. Let's unpack both the biochemical mechanism and the real-world benchwork reality:"
        ]
        import random
        opener = thoughtful_openers[hash(text) % len(thoughtful_openers)]

        reply = f"""💡 **{opener}**
*(Evidence Status: **Curated Knowledge Base** • Parameters below represent **Typical Reported Literature Ranges** and must be empirically calibrated for your specific matrix)*

---

### 1. 🔬 Scientific Principle & Molecular Mechanism
{c_mech}

---

### 2. 🧪 Typical Reported Protocol Range & Literature Benchmarks
• **Typical Reported Bench Conditions (Example Protocol Range):** {c_params}
• **Typical Published Benchmark Range (Context-Dependent):** {c_bench}

---

### 3. ⚠️ Foreseeable Experimental Pitfalls & Rescue Protocol
• **Foreseeable Pitfall:** {c_pitfalls}
• **Recommended Mitigation Protocol:** {c_rescue}

---

### 🎯 Connecting This to Your Proposal:
If you are incorporating this into your active project *("{live_title or 'Active Proposal'}")*:
• **In Section 3 (Aims):** Make sure your milestone defines a quantitative metric rather than a vague intention.
• **In Section 4 (Methodology):** Include untransformed wild-type host chassis as your negative baseline to prove specificity.
• **In Section 5:** Frame the mitigation protocol above using the Acknowledge-Clarify-Validate technique!"""

        actions = [
            {"label": "Adopt Verified Controls into Section 4", "icon": "🧪", "onClickJs": "copilotAdoptControls()"},
            {"label": "Adopt Technical Mitigation", "icon": "🛡️", "onClickJs": f"copilotAdoptPlanB('Foreseeable failure mode in {matched_concept['key']}', '{window_safe_escape(c_rescue)}')"},
            {"label": "Search Europe PMC Literature", "icon": "🔍", "onClickJs": f"copilotSubmitSearch('{matched_concept['key']} mechanism benchmark')"}
        ]

        suggestions = [
            {"text": f"🎙️ Grill me on {matched_concept['key']}", "prompt": f"grill me on {matched_concept['key']}"},
            {"text": f"📊 Compare {matched_concept['key']} in a table", "prompt": f"how does {matched_concept['key']} compare to alternative approaches in a table?"},
            {"text": "🎯 Draft specific aims for this", "prompt": f"Let us draft 3 decoupled specific aims based on {matched_concept['key']}"}
        ]

        return {
            "reply": reply,
            "actions": actions,
            "suggestions": suggestions,
            "thinking": thinking_steps,
            "evidence_status": "Curated knowledge",
            "concept": matched_concept["key"]
        }

    # CASE C: General Knowledge & Non-Biotech Science / Computing / History / Philosophy
    else:
        is_bio_term = bool(re.search(
            r'\b(bio|biotech|biology|cell|cells|cellular|gene|genes|genetic|genomic|dna|rna|mrna|protein|proteins|'
            r'enzyme|enzymes|enzymatic|bacteria|bacterial|microbe|microbial|virus|viral|vector|plasmid|promoter|'
            r'chassis|host|assay|assays|substrate|pathogen|crispr|cas|cleavage|mutation|mutant|expression|'
            r'recombinant|purification|synthesis|t7|iptg|pichia|e\.?\s*coli|bl21|transfection|transformation|'
            r'bioreactor|fermentation|biocatalysis|bioremediation|antibody|antigen|vaccine|therapy|clinical|'
            r'oncology|cancer|tumor|probit|lod|triplicate|negative control|positive control)\b',
            lower
        ))

        is_gen_knowledge = bool(re.search(
            r'\b(quantum|relativity|gravity|black hole|astronomy|telescope|space|planet|planets|solar system|mars|'
            r'history|revolution|world war|roman|ancient|philosophy|stoicism|nietzsche|epistemology|ethics|'
            r'algorithm|algorithms|programming|python|coding|neural network|machine learning|artificial intelligence|'
            r'deep learning|cpu|gpu|hardware|blockchain|bitcoin|cryptocurrency|calculus|algebra|physics|astrophysics|'
            r'chemistry|thermodynamics|entropy|mechanics|electricity|magnetism|optics)\b',
            lower
        ))

        # SUB-CASE C1: General Knowledge, Tech, Physics, History & Philosophy
        if is_gen_knowledge and not is_bio_term:
            thinking_steps.append("Identified general academic inquiry: non-biotech science, technology, history, or philosophy.")
            thinking_steps.append("Formulating structured educational explanation with intuitive analogies and real-world applications.")

            engine_links = get_search_engine_links(text) if get_search_engine_links else {}

            reply = f"""🧠 **Let's Explore That Concept:**

### 1. 💡 The Core Principle in Plain Terms
When we break down **"{text}"**, the foundational concept comes down to how underlying systems interact:
• Just like how complex cellular networks rely on basic molecular rules, this domain operates on elegant fundamental principles that govern how information, energy, or structure behaves.
• In everyday life, this principle allows us to predict behavior, optimize systems, and solve problems that initially seem paradoxical.

---

### 2. ⚙️ How It Works & Key Dynamics
• **The Mechanism:** The system functions through observable laws—balancing inputs, state transitions, and constraints to reach an equilibrium or produce a targeted output.
• **The Trade-Off:** Just like biological systems balance fidelity against metabolic cost, here too there is always a balance between precision, resources, and theoretical limits.

---

### 3. 🌍 Real-World Significance & Modern Relevance
• This concept underpins transformative advances across modern science and technology, reshaping how researchers model complex phenomena from subatomic particles to decentralized networks.

---

💡 **Where would you like to take this?**
We can search the live web for the latest deep-dive articles, look up foundational papers, or connect this logic back to bioengineering!"""

            actions = [
                {"label": f"Search Web: {text[:20]}", "icon": "🌐", "onClickJs": f"quickSendCopilotPrompt('search web for {window_safe_escape(text[:25])}')"},
                {"label": "Search Google Scholar", "icon": "📚", "onClickJs": f"window.open('{engine_links.get('scholar', '#')}', '_blank')"},
                {"label": "Explain More Simply", "icon": "💡", "onClickJs": f"quickSendCopilotPrompt('Explain {window_safe_escape(text[:30])} in simple terms with an everyday analogy')"},
                {"label": "Back to Proposal Brainstorming", "icon": "🔬", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"}
            ]

            suggestions = [
                {"text": "🌐 Search Web for more details", "prompt": f"search web for {text[:30]}"},
                {"text": "💡 How does this relate to biotechnology?", "prompt": f"how does {text[:30]} connect to biotechnology or biophysics?"}
            ]

            return {
                "reply": reply,
                "actions": actions,
                "suggestions": suggestions,
                "thinking": thinking_steps,
                "concept": "general_knowledge",
                "engine_links": engine_links
            }

        # SUB-CASE C2: Open-Ended Biological Inquiry (Curiosity -> Hypothesis Translation)
        elif is_bio_term:
            thinking_steps.append("Open-ended biotechnology research inquiry.")
            thinking_steps.append("Grounding in BT_301 grant evaluation criteria: biological gap, quantitative benchmark, and decoupled aims.")

            reply = f"""🧠 **Let's Dissect That Thought:**

When thinking about **"{text}"** from a scientific investigator's perspective, we want to translate biological curiosity into a testable, publication-grade bioengineering hypothesis:

1. **The Core Biological Question:**
   What exact molecular mechanism, enzyme, or cellular pathway are we trying to influence or measure?

2. **The Quantitative Benchmark:**
   Every strong proposal needs a published gold-standard number to beat. What baseline metric (e.g. turnaround time in hours, limit of detection in copies/µL, or catalytic turnover kcat) will we measure our success against?

3. **The Decoupled Architecture:**
   How do we structure our specific aims so that if our initial expression or synthesis encounters yield hiccups, our downstream analytical characterization can still proceed using a surrogate standard?

---

💡 **Where should we take this?**
We can formulate this into **3 Strategic Pillars (Host Chassis, Molecular Tool, Biological Target)**, search recent peer-reviewed literature on Europe PMC, or draft decoupled specific aims!"""

            actions = [
                {"label": "Search Europe PMC Literature", "icon": "🔍", "onClickJs": f"copilotSubmitSearch('{window_safe_escape(text[:30])}')"},
                {"label": "Draft 3 Decoupled Aims", "icon": "🎯", "onClickJs": f"quickSendCopilotPrompt('Let us draft 3 decoupled specific aims based on {window_safe_escape(text[:30])}')"},
                {"label": "Explore Gene Therapy", "icon": "🧬", "onClickJs": "quickSendCopilotPrompt('can we talk about gene therapy')"},
                {"label": "Explore Plastic Bioremediation", "icon": "♻️", "onClickJs": "quickSendCopilotPrompt('Let us brainstorm an engineered enzyme project for plastic degradation')"}
            ]

            suggestions = [
                {"text": "💡 How do we beat the Host-Swap Trap?", "prompt": "How do we make our project novel and beat the Host-Swap Trap?"},
                {"text": "🎙️ Grill me on this idea", "prompt": "grill me on this proposal"},
                {"text": "📋 Review proposal structure", "prompt": "Let us review the structure of my active proposal"}
            ]

            return {
                "reply": reply,
                "actions": actions,
                "suggestions": suggestions,
                "thinking": thinking_steps,
                "concept": "biological_exploration"
            }

        # SUB-CASE C3: Natural Conversational Fallback (No robotic template forcing)
        else:
            thinking_steps.append("Open conversational dialogue.")
            thinking_steps.append("Responding naturally and exploring the inquiry with intellectual curiosity.")

            engine_links = get_search_engine_links(text) if get_search_engine_links else {}

            reply = f"""💡 **That's an interesting question: "{text}"**

Let's look at this thoughtfully:
• **The Big Picture:** What particular perspective or application are you most curious about exploring here?
• **Finding Evidence:** We can query live web indices or academic literature to see what the latest consensus or debate is.
• **Project Connection:** If you're looking for inspiration for your academic writing, we can connect this curiosity back to a novel biotechnology or research hypothesis!

Would you like to search the web for the latest updates on this, explore the concept deeper, or bounce around new proposal ideas?"""

            actions = [
                {"label": f"Search Web: {text[:20]}", "icon": "🌐", "onClickJs": f"quickSendCopilotPrompt('search web for {window_safe_escape(text[:25])}')"},
                {"label": "Search Google Scholar", "icon": "📚", "onClickJs": f"window.open('{engine_links.get('scholar', '#')}', '_blank')"},
                {"label": "Brainstorm Proposal Ideas", "icon": "🧠", "onClickJs": "quickSendCopilotPrompt('Brainstorm 3 high-impact biotechnology project ideas with me')"}
            ]

            suggestions = [
                {"text": "🌐 Search Web for this topic", "prompt": f"search web for {text[:30]}"},
                {"text": "🎯 Review My Specific Aims", "prompt": "Let us review and refine our 3 specific aims"}
            ]

            return {
                "reply": reply,
                "actions": actions,
                "suggestions": suggestions,
                "thinking": thinking_steps,
                "concept": "open_conversation",
                "engine_links": engine_links
            }


def window_safe_escape(text: str) -> str:
    """Escapes strings safely for JavaScript parameter embedding."""
    if not text:
        return ""
    clean = str(text).replace("\\", "\\\\").replace("'", "\\'").replace('"', '&quot;')
    clean = re.sub(r'[\r\n]+', ' ', clean).strip()
    return clean


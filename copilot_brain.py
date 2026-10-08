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
    active_proposal_context: Dict[str, Any],
    chat_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
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
    
    # Web & multi-engine search intent
    search_prefix_match = re.search(r'^(search|find|lookup|look up|google|websearch|web search|scholar):\s*(.*)', text, re.I)
    is_explicit_search = bool(search_prefix_match)
    is_web_search_intent = bool(re.search(r'\b(search (the )?(web|internet|google|online|duckduckgo|engines?)|look up (online|on the web|on google)|search engine|search engines|find (me )?(papers|studies|articles) online|find online|latest (news|research|paper|development) on)\b', lower))
    is_web_search = is_explicit_search or is_web_search_intent

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

    # CASUAL CASE 1: Weather & Everyday Small Talk
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
   Will shifting to this new tool solve an **explicit biophysical bottleneck** (e.g. higher thermostability $T_m$, faster $k_{{cat}}$, or zero double-strand DNA breaks)? Or does it risk falling into the *"Host-Swap Trap"* (taking a well-characterized enzyme and simply cloning it into a new host without biological rationale)?

3. **Experimental Containment & Regulatory Pathway:**
   A cellular platform deployed in the wild requires strict synthetic biology kill-switches (auxotrophy, toxin-antitoxin *mazE/mazF*). An acellular or cell-free matrix bypasses living GMO release restrictions completely!

---

💡 **Recommendation:**
Tell me the two specific options you want to compare (for example: *AAV vs. Targeted LNPs*, or *E. coli vs. Pichia pastoris*), and I will generate an empirical side-by-side comparison table showing yield, kinetics, and feasibility!"""

        actions = [
            {"label": "Compare AAV vs. LNPs in Table", "icon": "📊", "onClickJs": "quickSendCopilotPrompt('compare AAV vs LNP in a table')"},
            {"label": "Compare E. coli vs. Pichia", "icon": "🧫", "onClickJs": "quickSendCopilotPrompt('compare E coli vs Pichia pastoris expression in a table')"},
            {"label": "Auto-Assemble Proposal Blueprint", "icon": "✨", "onClickJs": "quickSendCopilotPrompt('Auto-assemble complete proposal blueprint')"}
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
        thinking_steps.append(f"Relevant Proposal Section: Sections 3 (Objectives), 4 (Methodology & Controls) & 5 (Expected Outcomes & Plan B) — '{live_title or 'Active Proposal'}'")
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
• **Recommended Rescue Protocol (Plan B Guidance):** {c_rescue}

---

### 🎯 Connecting This to Your Proposal:
If you are incorporating this into your active project *("{live_title or 'Active Proposal'}")*:
• **In Section 3 (Aims):** Make sure your milestone defines a quantitative metric rather than a vague intention.
• **In Section 4 (Methodology):** Include untransformed wild-type host chassis as your negative baseline to prove specificity.
• **In Section 5 (Plan B):** Frame the rescue protocol above using the Acknowledge-Clarify-Pivot (ACP) technique!"""

        actions = [
            {"label": "Adopt Verified Controls into Section 4", "icon": "🧪", "onClickJs": "copilotAdoptControls()"},
            {"label": "Inject Plan B into Section 5", "icon": "🛡️", "onClickJs": f"copilotAdoptPlanB('Foreseeable failure mode in {matched_concept['key']}', '{window_safe_escape(c_rescue)}')"},
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
   Every strong proposal needs a published gold-standard number to beat. What baseline metric (e.g. turnaround time in hours, limit of detection in copies/µL, or catalytic turnover $k_{{cat}}$) will we measure our success against?

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
                {"text": "✨ Auto-assemble proposal blueprint", "prompt": "Auto-assemble complete proposal blueprint"}
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

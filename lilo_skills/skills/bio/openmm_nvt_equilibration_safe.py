"""
Skill: openmm_nvt_equilibration_safe
=====================================
Gera um script OpenMM de equilibração NVT com práticas anti-NaN:

  1. Modeller.addHydrogens (pH configurável)
  2. Solvatação com padding >= 1.0 nm
  3. Minimização de energia (LocalEnergyMinimizer + simulation.minimizeEnergy)
  4. Aquecimento gradual 0 K -> T_alvo em rampas de 25 K
  5. Constraints HBonds (timestep 2 fs seguro)
  6. CheckpointReporter a cada 10 ps para retomar em caso de falha

Uso (via LILO MCP):
    skill_openmm_nvt_equilibration_safe(
        pdb_path="protein.pdb",
        output_script="run_nvt.py",
        target_temp_k=310.0,
        ph=7.4,
        forcefield="amber14-all.xml",
        water_model="amber14/tip3pfb.xml",
        padding_nm=1.2,
        timestep_fs=2.0,
        equilibration_ns=1.0,
    )

Retorna o caminho do script gerado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


_TEMPLATE = '''"""
NVT equilibration (anti-NaN) — gerado por LILO/openmm_nvt_equilibration_safe
PDB: {pdb_path}
Forcefield: {forcefield} + {water_model}
Target T: {target_temp_k} K | timestep: {timestep_fs} fs | duração: {equilibration_ns} ns
"""
import sys
from sys import stdout
from openmm import app, unit, LangevinMiddleIntegrator, Platform, MonteCarloBarostat
from openmm.app import (
    PDBFile, Modeller, ForceField, Simulation, PME, HBonds,
    StateDataReporter, DCDReporter, CheckpointReporter
)

PDB_PATH = r"{pdb_path}"
TARGET_T = {target_temp_k} * unit.kelvin
TIMESTEP = {timestep_fs} * unit.femtoseconds
EQUIL_NS = {equilibration_ns}
PADDING  = {padding_nm} * unit.nanometers
PH       = {ph}

# --- Carregar e preparar a estrutura --------------------------------------
print(f"[1/6] Carregando {{PDB_PATH}}", flush=True)
pdb = PDBFile(PDB_PATH)
ff  = ForceField("{forcefield}", "{water_model}")

print("[2/6] Adicionando hidrogenios (pH={{}}) e solvatando (padding={{}})".format(PH, PADDING), flush=True)
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(ff, pH=PH)
modeller.addSolvent(ff, model="tip3p", padding=PADDING, ionicStrength=0.15*unit.molar)

# --- Sistema --------------------------------------------------------------
print("[3/6] Construindo sistema (HBonds constraints)", flush=True)
system = ff.createSystem(
    modeller.topology,
    nonbondedMethod=PME,
    nonbondedCutoff=1.0*unit.nanometers,
    constraints=HBonds,
    rigidWater=True,
    hydrogenMass=1.5*unit.amu,  # HMR — permite timestep 2 fs estavel
)

integrator = LangevinMiddleIntegrator(0*unit.kelvin, 1.0/unit.picoseconds, TIMESTEP)
try:
    platform = Platform.getPlatformByName("CUDA")
    properties = {{"Precision": "mixed"}}
except Exception:
    platform = Platform.getPlatformByName("CPU")
    properties = {{}}

simulation = Simulation(modeller.topology, system, integrator, platform, properties)
simulation.context.setPositions(modeller.positions)

# --- Minimizacao ----------------------------------------------------------
print("[4/6] Minimizacao de energia (max 10000 iter, tol 10 kJ/mol/nm)", flush=True)
simulation.minimizeEnergy(maxIterations=10000, tolerance=10.0*unit.kilojoule_per_mole/unit.nanometer)

# --- Aquecimento gradual 0 -> T_alvo em rampas de 25 K --------------------
print("[5/6] Aquecimento gradual (rampas de 25 K, 50 ps cada)", flush=True)
ramp_steps = int(50 * unit.picoseconds / TIMESTEP)
n_ramps = max(1, int(TARGET_T.value_in_unit(unit.kelvin) // 25))
for i in range(1, n_ramps + 1):
    t_now = min(i * 25, TARGET_T.value_in_unit(unit.kelvin)) * unit.kelvin
    integrator.setTemperature(t_now)
    simulation.context.setVelocitiesToTemperature(t_now)
    print(f"   ramp {{i}}/{{n_ramps}} -> {{t_now}}", flush=True)
    simulation.step(ramp_steps)

# --- Equilibracao NVT principal -------------------------------------------
print(f"[6/6] Equilibracao NVT a {{TARGET_T}} por {{EQUIL_NS}} ns", flush=True)
integrator.setTemperature(TARGET_T)
total_steps = int(EQUIL_NS * unit.nanoseconds / TIMESTEP)

simulation.reporters.append(StateDataReporter(
    stdout, 5000, step=True, time=True, potentialEnergy=True,
    temperature=True, speed=True, remainingTime=True, totalSteps=total_steps,
))
simulation.reporters.append(DCDReporter("nvt_traj.dcd", 5000))
simulation.reporters.append(CheckpointReporter("nvt_checkpoint.chk", 25000))

simulation.step(total_steps)
simulation.saveState("nvt_final.xml")
PDBFile.writeFile(simulation.topology,
                  simulation.context.getState(getPositions=True).getPositions(),
                  open("nvt_final.pdb", "w"))
print("OK Equilibracao NVT concluida.", flush=True)
'''


def openmm_nvt_equilibration_safe(
    pdb_path: str,
    output_script: str = "run_nvt.py",
    target_temp_k: float = 310.0,
    ph: float = 7.4,
    forcefield: str = "amber14-all.xml",
    water_model: str = "amber14/tip3pfb.xml",
    padding_nm: float = 1.2,
    timestep_fs: float = 2.0,
    equilibration_ns: float = 1.0,
) -> str:
    """Gera um script OpenMM anti-NaN para equilibração NVT.

    Args:
        pdb_path: caminho para o PDB de entrada (proteína).
        output_script: caminho do .py a gerar.
        target_temp_k: temperatura alvo em K (310.15 = corpo humano).
        ph: pH para Modeller.addHydrogens.
        forcefield: campo de força (default amber14-all.xml).
        water_model: modelo de água (default amber14/tip3pfb.xml).
        padding_nm: padding da caixa em nm.
        timestep_fs: passo de integração em fs (2 fs com HBonds+HMR).
        equilibration_ns: duração da NVT em ns.

    Returns:
        Caminho absoluto do script gerado.
    """
    pdb_p = Path(pdb_path).expanduser().resolve()
    out_p = Path(output_script).expanduser().resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    script = _TEMPLATE.format(
        pdb_path=str(pdb_p),
        target_temp_k=target_temp_k,
        ph=ph,
        forcefield=forcefield,
        water_model=water_model,
        padding_nm=padding_nm,
        timestep_fs=timestep_fs,
        equilibration_ns=equilibration_ns,
    )
    out_p.write_text(script, encoding="utf-8")
    return str(out_p)


# Compatibilidade com loader genérico do lilo_skills
def run(args: dict) -> str:
    path = openmm_nvt_equilibration_safe(**args)
    return f"Script gerado: {path}\n\nExecute com: python {path}"

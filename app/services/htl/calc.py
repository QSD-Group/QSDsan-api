"""
HTL diesel-production calculation (MDSP, GWP) from sludge mass.

Heavy: imports exposan.htl.create_model and chaospy. The built model is
cached per warm Lambda container behind a lock, since biosteam's global
flowsheet/settings state isn't concurrency-safe and FastAPI's thread pool
can run handlers concurrently.
"""

import threading

from chaospy import distributions as shape  # chaospy version 4.3.17

from exposan.htl import create_model  # exposan version: PyPI exposan==1.4.1 (see pyproject.toml/uv.lock)

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Build (once per warm container) or return the cached HTL model."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            model = create_model(
                plant_size=True,
                feedstock='sludge',
                include_CFs_as_metrics=False,
                include_other_metrics=False,
                include_other_CFs_as_metrics=False,
            )
            param = model.parameter
            sys = model.system
            stream = sys.flowsheet.stream
            raw_wastewater = stream.feedstock_assumed_in_wastewater
            dist = shape.Uniform(12618039, 18927059)

            @param(name='plant_size',
                   element=raw_wastewater,
                   kind='coupled',
                   units='kg/hr',
                   baseline=15772549,
                   distribution=dist)
            def set_plant_size(i):
                raw_wastewater.F_mass = i

            _model = model
        return _model


def htl_calc(kg_hr, mmbtu_to_gal=0.12845, kg_to_lb=2.20462):
    """
    Take the existing dry metric tonnes of sludge and return the minimum diesel selling price and global warming potential of diesel.

    Parameters
    ----------
    kg_hr : float
        Sludge in kg/hr.
    mmbtu_to_gal : float, optional
        Conversion factor for MMBTU to gal diesel. Default is 0.12845.
        1 MMBTU = 0.12845 gal diesel.
    kg_to_lb : float, optional
        Conversion factor for kg to lb. Default is 2.20462.
        1 kg CO2 = 2.20462 lb CO2.

    Returns
    -------
    MDSP : float
        Minimum diesel selling price in $/gal diesel.
    GWP : float
        Global warming potential of diesel in lb CO2/gal diesel.

    Raises
    ------
    TypeError
        If kg_hr is not a float.
    TypeError
        If mmbtu_to_gal is not a float.
    TypeError
        If kg_to_lb is not a float.

    Example
    -------
    htl_calc(15772549)
    >>> (2.5, 10)

    Notes
    -----
    1. If used in other parts, make sure to convert the sludge to kg/hr.
    2. The MSDP is in $/gal diesel, which can be converted to various other units.
    3. The GWP is in lb CO2/gal diesel, which can be converted to various other units.
    """

    if not isinstance(kg_hr, (int, float)):
        raise TypeError("Sludge should be a float.")
    if not isinstance(mmbtu_to_gal, (int, float)):
        raise TypeError("MMBTU to gal should be a float.")
    if not isinstance(kg_to_lb, (int, float)):
        raise TypeError("KG to lb should be a float.")

    model = _get_model()
    plant_size = model.parameters[-1]
    plant_size.baseline = kg_hr

    # The HTL system's H2SO4/H2 ReversedSplitter units (S200, S300) execute
    # before the reagent-demand units they're supposed to reflect (AcidEx,
    # MemDis, HT/HC), so a single simulate() reports last call's reagent
    # demand, not this call's -- one full pass behind. A priming pass
    # flushes the lag; verified stable and history-independent across
    # varying kg_hr, so no third pass is needed.
    model.metrics_at_baseline()
    df = model.metrics_at_baseline()

    MSDP, GWP = [m for m in model.metrics if m.name in ('MDSP', 'GWP diesel')]

    return MSDP.get(), GWP.get() * mmbtu_to_gal * kg_to_lb

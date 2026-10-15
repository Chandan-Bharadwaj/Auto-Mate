from MateCore.algorithm import AlgorithmResult, PartMatch
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.mate_match import MateMatch
from MateCore.MateFit.fits import FitResult
from MateCore.mate_report import build_mate_report, format_mate_report, pairing_reason


def _ref(part: str, face: str) -> SurfaceRef:
    return SurfaceRef(part, part, face, None, None, part_id=part)


def test_mate_report_lists_surface_pairings_and_reasons():
    a1, a2 = _ref("A", "Face1"), _ref("A", "Face2")
    b1, b2 = _ref("B", "Face1"), _ref("B", "Face2")
    ctx = DocumentContext(
        "Doc",
        (
            DocumentObjectContext(
                "A",
                "A",
                "Part",
                "part",
                (),
                (a1, a2),
                (PartContext("A", "A", "A", faces=(a1, a2)),),
            ),
            DocumentObjectContext(
                "B",
                "B",
                "Part",
                "part",
                (),
                (b1, b2),
                (PartContext("B", "B", "B", faces=(b1, b2)),),
            ),
        ),
    )
    request = RecognitionRequest(ctx, (a1, a2))
    fit = FitResult(ok=True, fit_class="clearance", gap=0.02, residual=0.01)
    match = MateMatch(
        faces=(b1, b2),
        score=0.9,
        part_id="B",
        metadata={"pose_residual": 0.05, "fit_classes": ["clearance"]},
        pairs=(((a1,), (b1,)),),
        dof=1,
        fits=(fit,),
    )
    result = AlgorithmResult(part_matches=(PartMatch("B", "B", (match,), score=0.9),))
    report = build_mate_report(request, result)
    text = "\n".join(format_mate_report(report))
    assert "mating report" in text
    assert "Mate #1: B" in text
    assert "A.Face1  ->  B.Face1" in text
    assert "reason:" in text
    assert "fit: clearance" in text
    assert "pose_residual=0.05" in pairing_reason(match, 0)

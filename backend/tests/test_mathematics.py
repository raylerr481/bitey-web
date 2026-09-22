from app.core.mathematics import analyze, calculate

def test_arithmetic():
    result = calculate("10 + 5 * 2")
    assert result["ok"] is True
    assert result["result"] == 20

def test_percentage():
    result = analyze("porcentaje de 25 sobre 100")
    assert result["operation"] == "percentage"
    assert result["result"] == 25

def test_cagr():
    result = analyze("CAGR 100 121 2")
    assert round(result["result"], 6) == round(0.1, 6)

def test_statistics():
    result = analyze("promedio 2 4 6")
    assert result["result"] == 4

from kr_gov_job_mcp.analysis.alio_institution_context import (
    extract_board_fields,
    extract_main_business_rows,
    summarize_main_business,
)


def test_extract_main_business_rows_and_summary() -> None:
    html = """
    <table>
      <tr>
        <th>사업구분</th><th>2025년 결산</th><th>2026년 예산</th><th>비고</th>
      </tr>
      <tr>
        <td>운영</td><td>6,806</td><td>8,966</td><td>운영.hwp</td>
      </tr>
      <tr>
        <td>사업<br/>수탁사업</td><td>50,448</td><td>56,012</td><td>사업.hwp</td>
      </tr>
      <tr><td>기준일</td><td>2025년 12월 31일</td></tr>
    </table>
    """

    rows = extract_main_business_rows(html)
    summary = summarize_main_business(rows, "보건의료데이터 표준화")

    assert rows[0]["name"] == "운영"
    assert rows[0]["growth_amount"] == 2160
    assert rows[1]["name"] == "사업 수탁사업"
    assert rows[1]["latest_amount"] == 56012
    assert summary is not None
    assert "가장 큰 규모는 사업 수탁사업" in summary
    assert "가장 높은 성장성은 운영" in summary


def test_extract_board_fields_keeps_point_and_action_plan_separate() -> None:
    html = """
    <li>
      <p class="tit"><span>지적사항</span></p>
      <div class="con"><div class="terms-list"><p>데이터가 안전하게 관리될 수 있도록 노력할 것</p></div></div>
    </li>
    <li>
      <p class="tit"><span>지적사항 첨부파일</span></p>
      <div class="con"><div class="bt-list"><p><a>지적사항.hwpx</a></p></div></div>
    </li>
    <li>
      <p class="tit"><span>시정조치 계획</span></p>
      <div class="con"><div class="terms-list"><p>DR센터 구축 컨설팅 추진<br/>후속 예산확보</p></div></div>
    </li>
    """

    fields = extract_board_fields(html)

    assert fields["지적사항"] == "데이터가 안전하게 관리될 수 있도록 노력할 것"
    assert fields["지적사항 첨부파일"] == "지적사항.hwpx"
    assert fields["시정조치 계획"] == "DR센터 구축 컨설팅 추진 후속 예산확보"

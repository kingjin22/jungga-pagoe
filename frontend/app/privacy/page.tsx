import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "개인정보처리방침 | 정가파괴",
  description: "정가파괴 개인정보처리방침",
};

export default function PrivacyPage() {
  const updatedAt = "2026년 2월 20일";

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-black text-gray-900 mb-2">개인정보처리방침</h1>
      <p className="text-sm text-gray-400 mb-10">시행일: {updatedAt}</p>

      <div className="prose prose-sm max-w-none text-gray-700 space-y-8">

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">1. 수집하는 개인정보 항목</h2>
          <p>정가파괴(이하 "서비스")는 다음과 같은 개인정보를 수집합니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li><strong>딜 제보 시:</strong> 닉네임(선택), 딜 내용(제목·가격·링크·설명)</li>
            <li><strong>자동 수집:</strong> 접속 IP, 브라우저 종류, 방문 시각, 클릭 이벤트(익명 통계)</li>
          </ul>
          <p className="mt-2">회원가입 또는 로그인 기능을 운영하지 않으며, 이메일·전화번호 등 식별 정보는 수집하지 않습니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">2. 개인정보의 수집 및 이용 목적</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>딜 제보 접수 및 심사</li>
            <li>서비스 운영 통계 분석 (익명 집계)</li>
            <li>부정 사용 방지 및 서비스 보안</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">3. 개인정보의 보유 및 이용 기간</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>딜 제보 데이터:</strong> 제보 처리 완료 후 90일 보관 후 삭제</li>
            <li><strong>접속 로그(IP 등):</strong> 3개월 보관 후 자동 삭제</li>
            <li>관련 법령에 별도 보존 기간이 정해진 경우 해당 기간을 따릅니다.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">4. 개인정보의 제3자 제공</h2>
          <p>서비스는 이용자의 개인정보를 원칙적으로 외부에 제공하지 않습니다. 다만 아래의 경우는 예외로 합니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>이용자가 사전에 동의한 경우</li>
            <li>법령의 규정에 의거하거나 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">5. 개인정보의 파기</h2>
          <p>보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다. 전자적 파일 형태는 복구 불가능한 방법으로 영구 삭제하며, 종이 문서는 분쇄 또는 소각합니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">6. 쿠키(Cookie) 사용</h2>
          <p>서비스는 서비스 개선을 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정을 통해 거부할 수 있으며, 이 경우 일부 서비스 이용이 제한될 수 있습니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">7. 제휴 마케팅 및 외부 링크</h2>
          <p>본 서비스의 일부 링크는 <strong>쿠팡 파트너스</strong> 등 제휴 마케팅 프로그램의 일환입니다. 이용자가 해당 링크를 통해 구매하면 서비스는 수수료를 받을 수 있습니다. 이는 이용자에게 추가 비용을 발생시키지 않습니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">8. 이용자의 권리</h2>
          <p>이용자는 언제든지 자신의 개인정보에 대한 열람, 수정, 삭제를 요청할 수 있습니다. 문의는 아래 개인정보 보호책임자에게 연락하시기 바랍니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">9. 개인정보 보호책임자</h2>
          <ul className="list-none space-y-1">
            <li><strong>담당:</strong> 정가파괴 운영팀</li>
            <li><strong>이메일:</strong> contact@jungga-pagoe.com</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">10. 개정 이력</h2>
          <p>본 방침은 {updatedAt}부터 시행됩니다. 내용이 변경될 경우 서비스 내 공지를 통해 안내합니다.</p>
        </section>

      </div>
    </div>
  );
}

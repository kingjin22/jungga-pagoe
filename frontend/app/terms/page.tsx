import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "이용약관 | 정가파괴",
  description: "정가파괴 이용약관",
};

export default function TermsPage() {
  const updatedAt = "2026년 2월 20일";

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-black text-gray-900 mb-2">이용약관</h1>
      <p className="text-sm text-gray-400 mb-10">시행일: {updatedAt}</p>

      <div className="prose prose-sm max-w-none text-gray-700 space-y-8">

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제1조 (목적)</h2>
          <p>본 약관은 정가파괴(이하 "서비스")가 제공하는 핫딜·최저가 정보 서비스 이용과 관련하여 서비스와 이용자 간의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제2조 (서비스 내용)</h2>
          <p>서비스는 다음을 제공합니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>쿠팡, 네이버쇼핑, 커뮤니티 등의 할인 딜 정보 수집 및 제공</li>
            <li>카테고리·브랜드별 딜 탐색</li>
            <li>딜 제보 접수 및 심사</li>
          </ul>
          <p className="mt-2">서비스는 정보 제공을 목적으로 하며, 직접 판매·구매 계약의 당사자가 아닙니다. 실제 거래는 각 쇼핑몰에서 이루어집니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제3조 (제휴 마케팅 고지)</h2>
          <p>서비스 내 일부 링크는 <strong>쿠팡 파트너스 제휴 링크</strong>입니다. 이용자가 해당 링크를 통해 상품을 구매할 경우, 서비스는 판매 금액의 일부를 수수료로 지급받습니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>수수료는 이용자의 구매 금액에 추가되지 않습니다.</li>
            <li>제휴 관계는 서비스의 딜 정보 선정에 영향을 미치지 않습니다.</li>
            <li>모든 딜은 실제 할인율(정가 대비)이 확인된 경우에만 게재됩니다.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제4조 (정보의 정확성)</h2>
          <p>서비스는 최신 가격·재고 정보를 제공하기 위해 노력하나, 다음의 경우가 발생할 수 있습니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>가격은 실시간으로 변동될 수 있으며, 서비스에 표시된 가격과 실제 판매 가격이 다를 수 있습니다.</li>
            <li>딜이 조기 종료되거나 품절될 수 있습니다.</li>
          </ul>
          <p className="mt-2">최종 구매 전 반드시 해당 쇼핑몰에서 가격을 확인하시기 바랍니다. 서비스는 가격 오류로 인한 손해에 대해 법적 책임을 지지 않습니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제5조 (딜 제보)</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>이용자는 정확한 딜 정보만 제보해야 합니다.</li>
            <li>허위 정보, 스팸, 사기성 링크, 광고성 내용을 포함한 제보는 삭제되며, 제보 기능이 제한될 수 있습니다.</li>
            <li>제보된 내용은 서비스의 심사를 거쳐 게재 여부가 결정됩니다.</li>
            <li>제보자는 제보 내용의 정확성에 대한 책임을 집니다.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제6조 (금지 행위)</h2>
          <p>이용자는 다음 행위를 해서는 안 됩니다.</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>서비스 내 악성 코드·스팸 링크 삽입</li>
            <li>자동화된 수단으로 서비스를 과부하시키는 행위</li>
            <li>타인의 권리를 침해하거나 불법적인 목적으로 서비스를 이용하는 행위</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제7조 (서비스 변경 및 중단)</h2>
          <p>서비스는 운영상·기술상의 이유로 사전 통지 없이 서비스의 일부 또는 전부를 변경하거나 중단할 수 있습니다. 이로 인한 이용자의 손해에 대해서는 책임지지 않습니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">제8조 (준거법 및 관할법원)</h2>
          <p>본 약관은 대한민국 법률에 따라 해석되며, 서비스와 이용자 간 분쟁은 관할 법원에서 해결합니다.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-gray-900 mb-2">부칙</h2>
          <p>본 약관은 {updatedAt}부터 시행됩니다.</p>
        </section>

      </div>
    </div>
  );
}

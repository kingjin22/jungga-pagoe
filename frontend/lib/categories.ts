export const CATEGORIES: Record<string, { name: string; slug: string; desc: string; keywords: string }> = {
  "신발": {
    name: "신발",
    slug: "sneakers",
    desc: "나이키, 아디다스, 뉴발란스 등 인기 브랜드 신발 최저가 할인 정보. 정가 대비 최대 50% 할인 딜을 모았습니다.",
    keywords: "나이키 할인, 아디다스 세일, 뉴발란스 최저가, 운동화 특가"
  },
  "전자기기": {
    name: "전자기기",
    slug: "electronics",
    desc: "갤럭시, 아이폰, 에어팟, 노트북 등 전자기기 최저가. 공식 정가 대비 실제 할인 딜만 모았습니다.",
    keywords: "갤럭시 할인, 아이폰 최저가, 에어팟 세일, 노트북 특가"
  },
  "생활가전": {
    name: "생활가전",
    slug: "appliances",
    desc: "다이슨, LG, 삼성 생활가전 최저가 할인. 청소기, 에어랩, 공기청정기 특가 딜을 모았습니다.",
    keywords: "다이슨 할인, LG 가전 세일, 삼성 가전 최저가"
  },
  "패션": {
    name: "패션",
    slug: "fashion",
    desc: "노스페이스, 나이키 의류 등 패션 브랜드 최저가. 정가 대비 할인 딜만 선별했습니다.",
    keywords: "노스페이스 할인, 패딩 최저가, 패션 세일"
  },
  "뷰티": {
    name: "뷰티",
    slug: "beauty",
    desc: "라로슈포제, 설화수, 다이슨 뷰티 등 코스메틱 최저가 할인 정보.",
    keywords: "화장품 할인, 스킨케어 최저가, 뷰티 세일"
  },
};

export function getCategoryBySlug(slug: string) {
  return Object.values(CATEGORIES).find(c => c.slug === slug);
}

export function getCategoryNameBySlug(slug: string) {
  return getCategoryBySlug(slug)?.name ?? null;
}

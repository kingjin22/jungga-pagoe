"use client";

import { useState } from "react";
import { Deal } from "@/lib/api";
import DealCard from "./DealCard";
import DealModal from "./DealModal";

interface DealGridProps {
  deals: Deal[];
}

export default function DealGrid({ deals }: DealGridProps) {
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
        {deals.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onClick={setSelectedDeal}
          />
        ))}
      </div>

      <DealModal
        deal={selectedDeal}
        onClose={() => setSelectedDeal(null)}
      />
    </>
  );
}

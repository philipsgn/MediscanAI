import { create } from 'zustand';
import { IDrugItem } from '@/types/medication';

export interface CabinetDrugItem extends IDrugItem {
  id: string;
  inputSource: 'prescription' | 'packaging' | 'manual';
  isActive: boolean; // Dùng để Tắt/Bật lúc phân tích
}

interface CabinetState {
  drugs: CabinetDrugItem[];
  addDrug: (drug: Omit<CabinetDrugItem, 'id' | 'isActive'>) => void;
  addDrugs: (drugs: Omit<CabinetDrugItem, 'id' | 'isActive'>[]) => void;
  updateDrug: (id: string, data: Partial<CabinetDrugItem>) => void;
  removeDrug: (id: string) => void;
  toggleActive: (id: string) => void;
  clearAll: () => void;
}

export const useCabinetStore = create<CabinetState>((set) => ({
  drugs: [],
  addDrug: (drug) => set((state) => ({
    drugs: [...state.drugs, { ...drug, id: crypto.randomUUID(), isActive: true }]
  })),
  addDrugs: (newDrugs) => set((state) => {
    const initializedDrugs = newDrugs.map(d => ({
      ...d,
      id: crypto.randomUUID(),
      isActive: true
    }));
    return { drugs: [...state.drugs, ...initializedDrugs] };
  }),
  updateDrug: (id, data) => set((state) => ({
    drugs: state.drugs.map(d => d.id === id ? { ...d, ...data } : d)
  })),
  removeDrug: (id) => set((state) => ({
    drugs: state.drugs.filter(d => d.id !== id)
  })),
  toggleActive: (id) => set((state) => ({
    drugs: state.drugs.map(d => d.id === id ? { ...d, isActive: !d.isActive } : d)
  })),
  clearAll: () => set({ drugs: [] })
}));

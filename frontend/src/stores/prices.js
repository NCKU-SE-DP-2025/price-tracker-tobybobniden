import { defineStore } from 'pinia';
import axios from 'axios';
import Categories from '@/constants/categories';

export const usePricesStore = defineStore('prices', {
    state: () => {
        const initialState = {
            categories: {},
            isLoading: false,
            errorMessage: '',
            updatedTime: null
        };
        Object.keys(Categories).forEach(category => {
            initialState.categories[category] = [];
        });
        return initialState;
    },
    actions: {
        async fetchPrices() {
            this.isLoading = true;
            this.errorMessage = '';
            Object.keys(Categories).forEach(category => {
                this.categories[category] = [];
            });
            try {
                // Fetch prices for each category
                const categoryNames = Object.values(Categories);
                
                for (const categoryName of categoryNames) {
                    try {
                        const response = await axios.get('http://localhost:8000/api/v1/prices/necessities-price', {
                            params: {
                                CategoryName: categoryName
                            }
                        });
                        
                        let data = response.data;

                        // Check if data is an error response
                        if (data && typeof data === 'object' && data.error) {
                            console.warn(`Error fetching ${categoryName}: ${data.error}`);
                            continue;
                        }

                        // Ensure data is an array
                        if (!Array.isArray(data)) {
                            console.warn(`Invalid data format for ${categoryName}: expected array`);
                            continue;
                        }

                        // Process the data
                        data.forEach(item => {
                            const categoryKey = Object.keys(Categories).find(
                                key => Categories[key] === item.類別
                            );
                            if (categoryKey) {
                                this.categories[categoryKey].push(item);
                            }
                        });
                    } catch (categoryError) {
                        console.warn(`Error fetching prices for ${categoryName}:`, categoryError.message);
                        // Continue with next category instead of failing entirely
                        continue;
                    }
                }
                
                this.updatedTime = new Date();
                this.updatedTime = this.updatedTime.toLocaleString('zh-TW', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                }).replace(/(\d{4})\/(\d{2})\/(\d{2}), (\d{2}):(\d{2}):(\d{2})/, "$1/$2/$3 $4:$5");
            } catch (error) {
                this.errorMessage = 'Error fetching prices: ' + error.message;
            } finally {
                this.isLoading = false;
            }
        },
    },
    getters: {
        getPricesByCategory: (state) => (category) => {
            return state.categories[category] || [];
        },
        getAllCategories: (state) => {
            return state.categories;
        },
        getProductList: (state) => (category) => {
            return state.categories[category].map(item => item.產品名稱);
        },
    }
});

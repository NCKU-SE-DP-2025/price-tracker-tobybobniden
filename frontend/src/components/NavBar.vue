<template>
    <nav class="navbar">
        <div class="title">
            <RouterLink to="/overview">價格追蹤小幫手</RouterLink>
        </div>
        <ul class="options" v-if="!isMobile">
            <li><RouterLink to="/overview">物價概覽</RouterLink></li>
            <li><RouterLink to="/trending">物價趨勢</RouterLink></li>
            <li><RouterLink to="/news">相關新聞</RouterLink></li>
            <li v-if="!isLoggedIn"><RouterLink to="/login">登入</RouterLink></li>
            <li v-else @click="logout">Hi, {{getUserName}}! 登出</li>
        </ul>
        <div class="hamburger" :class="{ active: menuOpen }" @click="toggleMenu" v-if="isMobile">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="mobile-menu" :class="{ active: menuOpen }" v-if="isMobile">
            <ul>
                <li><RouterLink to="/overview" @click="closeMenu">物價概覽</RouterLink></li>
                <li><RouterLink to="/trending" @click="closeMenu">物價趨勢</RouterLink></li>
                <li><RouterLink to="/news" @click="closeMenu">相關新聞</RouterLink></li>
                <li v-if="!isLoggedIn"><RouterLink to="/login" @click="closeMenu">登入</RouterLink></li>
                <li v-else @click="logout">Hi, {{getUserName}}! 登出</li>
            </ul>
        </div>
    </nav>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';

const menuOpen = ref(false);
const isMobile = ref(false);

const userStore = useAuthStore();
const isLoggedIn = computed(() => userStore.isLoggedIn);
const getUserName = computed(() => userStore.getUserName);

function logout() {
    userStore.logout();
    closeMenu();
}

function toggleMenu() {
    menuOpen.value = !menuOpen.value;
}

function closeMenu() {
    menuOpen.value = false;
}

function handleOutsideClick(event) {
    const navBarEl = document.querySelector('.navbar');
    if (menuOpen.value && navBarEl && !navBarEl.contains(event.target)) {
        menuOpen.value = false;
    }
}

function checkMobile() {
    isMobile.value = window.innerWidth <= 767;
}

onMounted(() => {
    checkMobile();
    window.addEventListener('resize', checkMobile);
    document.addEventListener('click', handleOutsideClick);
});

onBeforeUnmount(() => {
    window.removeEventListener('resize', checkMobile);
    document.removeEventListener('click', handleOutsideClick);
});
</script>

<style scoped>
.navbar {
    display: flex;
    justify-content: space-between;
    background-color: #f3f3f3;
    padding: 1.5em;
    height: 4.5em;
    width: 100%;
    align-items: center;
    box-shadow: 0 0 5px #000000;
}

.navbar ul {
    list-style: none;
    display: flex;
    justify-content: space-around;
}

.title > a{
    font-size: 1.4em;
    font-weight: bold;
    color: #2c3e50 !important;
}

.navbar li {
    color: #575B5D;
    margin: 0.5em;
    font-size: 1.2em;
}

.navbar li:hover{
    cursor: pointer;
    font-weight: bold;
}

.navbar a {
    text-decoration: none;
    color: #575B5D;
}

.hamburger {
    display: none;
    flex-direction: column;
    cursor: pointer;
    padding: 5px;
}

.hamburger span {
    width: 20px;
    height: 2px;
    background-color: #333;
    margin: 2px 0;
    transition: 0.3s;
}

.mobile-menu {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    width: 100%;
    background-color: #ffffff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    z-index: 1000;
}

.mobile-menu.active {
    display: block;
}

.mobile-menu ul {
    list-style: none;
    padding: 0;
}

.mobile-menu li {
    display: block;
    padding: 5px 20px;
    color: #666;
    font-size: 20px;
    transition: background-color 0.3s ease;
    text-decoration: none;
    cursor: pointer;
}

.mobile-menu li:hover {
    background-color: #f8f8f8;
    color: #333;
    font-weight: bold;
}

.mobile-menu a {
    display: block;
    padding: 5px 20px;
    text-decoration: none;
    color: #666;
    font-size: 20px;
    transition: background-color 0.3s ease;
}

.mobile-menu a:hover {
    background-color: #f8f8f8;
    color: #333;
}

.hamburger.active span:nth-child(1) {
    transform: rotate(-45deg) translate(-4px, 4px);
}

.hamburger.active span:nth-child(2) {
    opacity: 0;
}

.hamburger.active span:nth-child(3) {
    transform: rotate(45deg) translate(-4px, -4px);
}

/* Mobile styles */
@media (max-width: 767px) {

    .mobile-menu ul {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    }

    .mobile-menu li {
        width: 100%;
    }
    
    .options {
        display: none;
    }
    .hamburger {
        display: flex;
    }
}
</style>
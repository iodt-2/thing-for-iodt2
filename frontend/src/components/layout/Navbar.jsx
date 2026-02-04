import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Moon, Sun, Globe } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import { useTranslation } from 'react-i18next';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import TenantSelector from '@/components/tenant/TenantSelector';
import CurrentTenantBadge from '@/components/tenant/CurrentTenantBadge';

const Navbar = () => {
  const { theme, setTheme } = useTheme();
  const { i18n } = useTranslation();
  const [currentLang, setCurrentLang] = useState(i18n.language || 'en');

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  const changeLanguage = (lang) => {
    i18n.changeLanguage(lang);
    setCurrentLang(lang);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 z-30">
      <div className="h-full px-4 flex items-center justify-between">
        {/* Logo & Current Tenant Badge */}
        <div className="flex items-center space-x-4">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">TS</span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold text-gray-900 dark:text-white">TwinScale</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">Lite</span>
            </div>
          </Link>

          {/* Current Tenant Indicator */}
          <CurrentTenantBadge className="hidden md:flex" />
        </div>

        {/* Right side - Tenant Selector, Theme & Language */}
        <div className="flex items-center space-x-2">
          {/* Tenant Selector */}
          <TenantSelector className="hidden lg:flex" />
          {/* Language Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <Globe className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => changeLanguage('en')}>
                <span className={currentLang === 'en' ? 'font-bold' : ''}>English</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => changeLanguage('tr')}>
                <span className={currentLang === 'tr' ? 'font-bold' : ''}>Türkçe</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme Toggle */}
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

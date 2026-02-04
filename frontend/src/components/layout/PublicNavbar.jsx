import { Link, useLocation } from "react-router-dom";
import { Globe2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PublicNavbar = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const isActive = (path) => {
    return currentPath === path;
  };

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <Globe2 className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Ditto IoT Manager</span>
          </Link>
          <div className="flex items-center space-x-4">
            <Link to="/about">
              <Button
                variant={isActive("/about") ? "default" : "ghost"}
                className={cn(
                  "hover:scale-105 transition-transform",
                  isActive("/about") ? "bg-primary text-primary-foreground" : ""
                )}
              >
                About
              </Button>
            </Link>
            <Link to="/contact">
              <Button
                variant={isActive("/contact") ? "default" : "ghost"}
                className={cn(
                  "hover:scale-105 transition-transform",
                  isActive("/contact")
                    ? "bg-primary text-primary-foreground"
                    : ""
                )}
              >
                Contact
              </Button>
            </Link>
            <div className="h-6 w-px bg-border" />
            <Link to="/login">
              <Button
                variant="outline"
                className="hover:scale-105 transition-transform"
              >
                Log in
              </Button>
            </Link>
            <Link to="/register">
              <Button className="hover:scale-105 transition-transform">
                Sign up
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default PublicNavbar;

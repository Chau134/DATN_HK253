package com.example.serviceapiecommerce.security;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserAccountStatus;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.JwtService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtService jwtService;
    private final UserAccountRepository userAccountRepository;

    public JwtAuthenticationFilter(JwtService jwtService, UserAccountRepository userAccountRepository) {
        this.jwtService = jwtService;
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String token = bearerToken(request);
        if (token == null) {
            filterChain.doFilter(request, response);
            return;
        }

        try {
            JwtClaims claims = jwtService.parseAccessToken(token);
            UserAccount account = userAccountRepository.findByIdWithRoles(claims.userId())
                    .orElseThrow(() -> new IllegalArgumentException("user_not_found"));
            if (account.getStatus() != UserAccountStatus.ACTIVE) {
                throw new IllegalArgumentException("user_not_active");
            }

            List<GrantedAuthority> authorities = account.getRoles().stream()
                    .filter(role -> role.getActive() == null || role.getActive())
                    .map(role -> new SimpleGrantedAuthority("ROLE_" + role.getName()))
                    .map(GrantedAuthority.class::cast)
                    .toList();
            AuthenticatedUser principal = new AuthenticatedUser(
                    account.getId(),
                    account.getEmail(),
                    account.getPasswordHash(),
                    true,
                    authorities
            );
            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(principal, token, principal.getAuthorities());
            SecurityContextHolder.getContext().setAuthentication(authentication);
            filterChain.doFilter(request, response);
        } catch (RuntimeException exception) {
            SecurityContextHolder.clearContext();
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write("{\"error\":\"invalid_token\"}");
        }
    }

    private static String bearerToken(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return null;
        }
        String token = authorization.substring(7).trim();
        return token.isEmpty() ? null : token;
    }
}
